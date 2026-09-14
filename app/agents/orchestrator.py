"""LangGraph orchestrator for financial question answering."""

import re
import json
import time
import logging
from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, START, END

from app.config.settings import settings
from app.models.transaction import NormalizedTransaction, TransactionType
from app.models.schemas import ValidationInfo, AskResponse
from app.agents.state import AgentState
from app.analytics.engine import FinancialAnalyticsEngine
from app.tools.analytics_tools import registry
from app.tools.rag_tools import search_statement_text
from app.validation.validator import FinancialResultValidator
from app.observability.tracer import tracer

logger = logging.getLogger("financial_agent.orchestrator")


class FinancialAgentOrchestrator:
    """Orchestrates natural language intent classification, deterministic tool execution,
    result validation, and LLM explanation generation."""

    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("classify_intent", self.node_classify_intent)
        workflow.add_node("execute_tools", self.node_execute_tools)
        workflow.add_node("validate_results", self.node_validate_results)
        workflow.add_node("generate_response", self.node_generate_response)
        workflow.add_node("audit_response", self.node_audit_response)

        workflow.add_edge(START, "classify_intent")
        workflow.add_edge("classify_intent", "execute_tools")
        workflow.add_edge("execute_tools", "validate_results")
        workflow.add_edge("validate_results", "generate_response")
        workflow.add_edge("generate_response", "audit_response")
        workflow.add_edge("audit_response", END)

        return workflow.compile()

    def ask(
        self,
        question: str,
        transactions: List[NormalizedTransaction],
        session_id: Optional[str] = None
    ) -> AskResponse:
        trace = tracer.create_trace(
            name="financial_question_orchestrator",
            user_id=session_id,
            metadata={"question": question, "transaction_count": len(transactions)}
        )

        initial_state: AgentState = {
            "question": question,
            "session_id": session_id,
            "transactions": transactions,
            "intent": "general",
            "selected_tools": [],
            "tool_params": {},
            "tool_results": {},
            "relevant_transactions": [],
            "rag_context": None,
            "validation": ValidationInfo(),
            "final_answer": "",
            "confidence": 1.0,
            "error": None
        }

        start_time = time.time()
        with tracer.trace_span(trace, "langgraph_execution", input_data={"question": question}) as span_ctx:
            final_state = self.graph.invoke(initial_state)
            span_ctx["output"] = {
                "tools_used": final_state["selected_tools"],
                "validation_passed": final_state["validation"].is_valid
            }
        latency_ms = (time.time() - start_time) * 1000.0

        # Record metrics in real-time cost tracker
        from app.observability.tracer import cost_store
        model_name = settings.GEMINI_MODEL_NAME if settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY else (
            settings.OPENAI_MODEL_NAME if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY else "local-deterministic"
        )
        cost_record = cost_store.record_request(
            question=question,
            tools_used=final_state["selected_tools"],
            latency_ms=latency_ms,
            model_name=model_name,
            session_id=session_id
        )

        return AskResponse(
            question=question,
            answer=final_state["final_answer"],
            tools_used=final_state["selected_tools"],
            calculation_results=final_state["tool_results"],
            relevant_transactions=final_state["relevant_transactions"],
            confidence=final_state["confidence"],
            validation=final_state["validation"],
            source_info={
                "transactions_analyzed": len(transactions),
                "session_id": session_id,
                "cost_analytics": cost_record
            }
        )

    # ------------------ GRAPH NODES ------------------ #

    def node_classify_intent(self, state: AgentState) -> Dict[str, Any]:
        """Classify user intent and select appropriate deterministic tools."""
        q = state["question"].lower()
        selected_tools: List[str] = []
        tool_params: Dict[str, Dict[str, Any]] = {}

        # 1. Total credit and debit
        if any(kw in q for kw in ["total credit", "total debit", "credit and debit", "total spent and received", "income and expense"]):
            selected_tools.extend(["get_total_credits", "get_total_debits"])
        elif any(kw in q for kw in ["total credit", "total deposit", "money received", "how much did i receive", "how much money came in"]):
            selected_tools.append("get_total_credits")
        elif any(kw in q for kw in ["total debit", "total spent", "total expenses", "how much did i spend in total"]):
            selected_tools.append("get_total_debits")

        # 2. Monthly queries
        months = {
            "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
        }
        matched_month = None
        for m_name, m_num in months.items():
            if m_name in q:
                matched_month = m_num
                break

        if "month" in q or matched_month or "monthly" in q:
            selected_tools.append("get_monthly_summary")
            tool_params["get_monthly_summary"] = {"month": matched_month}

        # 3. Specific merchant spending
        merchant_match = re.search(
            r"(?:spend|spent|paid|charges?|at|on|to|for)\s+(?:at\s+|on\s+|to\s+|for\s+)?([A-Za-z0-9\.\'\s]{2,25})(?:\?|$)",
            state["question"],
            re.IGNORECASE
        )
        common_skip = {"in", "on", "at", "to", "for", "total", "most", "top", "all", "the", "my", "money", "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"}
        if merchant_match:
            candidate = merchant_match.group(1).strip()
            candidate = re.sub(r"^(?:at|on|to|for|with|in)\s+", "", candidate, flags=re.IGNORECASE).strip()
            if candidate.lower() not in common_skip and len(candidate) > 2:
                selected_tools.append("get_merchant_spending")
                tool_params["get_merchant_spending"] = {"merchant_name": candidate}

        # 4. Where did money go / Category breakdown
        if any(kw in q for kw in ["where did most of my money go", "where did my money go", "category", "breakdown", "spending breakdown"]):
            selected_tools.extend(["get_category_spending", "get_merchant_spending"])

        # 5. Where did money come from / Source breakdown
        if any(kw in q for kw in ["where did my money come from", "income source", "sources of money", "who paid me"]):
            selected_tools.append("get_money_received_sources")

        # 6. Highest or top transactions
        if any(kw in q for kw in ["highest credit", "largest deposit", "biggest deposit"]):
            selected_tools.append("get_highest_credit")
        elif any(kw in q for kw in ["highest debit", "largest expense", "biggest expense", "largest purchase", "highest transaction"]):
            selected_tools.append("get_highest_debit")
        elif any(kw in q for kw in ["top", "highest", "biggest", "largest"]):
            n_match = re.search(r"top\s+(\d+)", q)
            top_n = int(n_match.group(1)) if n_match else 10
            selected_tools.append("get_top_transactions")
            tool_params["get_top_transactions"] = {"n": top_n}

        # 7. Transaction counts
        if any(kw in q for kw in ["how many transactions", "transaction count", "count"]):
            selected_tools.append("get_transaction_count")

        # 8. Recurring or subscriptions
        if any(kw in q for kw in ["recurring", "subscription", "bills", "monthly charges"]):
            selected_tools.append("get_recurring_transactions")

        # 9. Balance summary
        if any(kw in q for kw in ["balance", "starting balance", "ending balance", "closing balance", "net flow"]):
            selected_tools.append("get_balance_summary")

        # 10. Average transaction
        if any(kw in q for kw in ["average transaction", "average spending", "average deposit"]):
            selected_tools.append("get_average_transaction")

        # 11. Textual / RAG context questions
        if any(kw in q for kw in ["policy", "fee", "disclaimer", "interest rate", "terms", "condition", "footnote", "account number", "routing"]):
            selected_tools.append("search_statement_text")
            tool_params["search_statement_text"] = {"query": state["question"], "statement_id": state.get("session_id")}

        # Deduplicate tools while preserving order
        unique_tools = []
        for t in selected_tools:
            if t not in unique_tools:
                unique_tools.append(t)

        # Fallback if no specific pattern matched: provide overall balance and counts
        if not unique_tools:
            unique_tools = ["get_total_credits", "get_total_debits", "get_balance_summary"]

        return {
            "selected_tools": unique_tools,
            "tool_params": tool_params,
            "intent": "financial_query"
        }

    def node_execute_tools(self, state: AgentState) -> Dict[str, Any]:
        """Execute selected tools deterministically."""
        engine = FinancialAnalyticsEngine(state["transactions"])
        tool_results: Dict[str, Any] = {}
        relevant_txns: List[NormalizedTransaction] = []
        rag_context_parts: List[str] = []

        for tool_name in state["selected_tools"]:
            params = state["tool_params"].get(tool_name, {})
            try:
                if tool_name == "search_statement_text":
                    res = search_statement_text(
                        query=params.get("query", state["question"]),
                        statement_id=params.get("statement_id", state.get("session_id"))
                    )
                    tool_results[tool_name] = res
                    for chunk in res.get("retrieved_chunks", []):
                        rag_context_parts.append(chunk["text"])
                else:
                    res = registry.execute(tool_name, engine, **params)
                    tool_results[tool_name] = res

                    # Collect relevant transactions if present in tool output
                    if "transactions" in res and isinstance(res["transactions"], list):
                        for raw_t in res["transactions"][:10]:
                            if isinstance(raw_t, dict):
                                try:
                                    relevant_txns.append(NormalizedTransaction(**raw_t))
                                except Exception:
                                    pass
            except Exception as e:
                tool_results[tool_name] = {"error": str(e)}

        # Deduplicate relevant transactions
        seen = set()
        deduped_rel = []
        for t in relevant_txns:
            if t.transaction_id not in seen:
                seen.add(t.transaction_id)
                deduped_rel.append(t)

        if "get_total_credits" in tool_results and "get_total_debits" in tool_results:
            cr_val = tool_results["get_total_credits"].get("total_credits", 0.0)
            dr_val = tool_results["get_total_debits"].get("total_debits", 0.0)
            tool_results["net_cash_flow"] = {"net_cash_flow": round(cr_val - dr_val, 2)}

        return {
            "tool_results": tool_results,
            "relevant_transactions": deduped_rel,
            "rag_context": "\n\n".join(rag_context_parts) if rag_context_parts else None
        }

    def node_validate_results(self, state: AgentState) -> Dict[str, Any]:
        """Validate transaction dataset and check that tool calculations succeeded."""
        val_info = FinancialResultValidator.validate_transactions_integrity(state["transactions"])
        flags = val_info.get("flags", [])

        # Check for tool errors
        for t_name, res in state["tool_results"].items():
            if isinstance(res, dict) and "error" in res:
                flags.append(f"Tool {t_name} returned error: {res['error']}")

        validation = ValidationInfo(
            is_valid=val_info.get("is_valid", True),
            grounded_in_tools=True,
            claims_verified=True,
            consistency_passed=len(flags) == 0,
            flags=flags
        )

        return {"validation": validation}

    def node_generate_response(self, state: AgentState) -> Dict[str, Any]:
        """Generate response explaining the verified calculation results."""
        prompt = self._build_explanation_prompt(
            question=state["question"],
            tool_results=state["tool_results"],
            rag_context=state["rag_context"]
        )

        answer = self._call_llm_or_fallback(prompt, state["tool_results"], state["question"])
        return {"final_answer": answer}

    def node_audit_response(self, state: AgentState) -> Dict[str, Any]:
        """Audit the final explanation against verified tool results to catch hallucinations."""
        audit_val = FinancialResultValidator.validate_llm_response(
            llm_response=state["final_answer"],
            tool_results=state["tool_results"]
        )

        current_val = state["validation"]
        merged_flags = list(current_val.flags) + audit_val.flags

        updated_val = ValidationInfo(
            is_valid=current_val.is_valid and audit_val.is_valid,
            grounded_in_tools=audit_val.grounded_in_tools,
            claims_verified=audit_val.claims_verified,
            consistency_passed=current_val.consistency_passed and audit_val.grounded_in_tools,
            flags=merged_flags
        )

        final_ans = state["final_answer"]
        if not audit_val.grounded_in_tools:
            final_ans += "\n\n*(Note: Audit check flagged potential numerical discrepancy; please refer to calculation results)*"

        return {
            "validation": updated_val,
            "final_answer": final_ans
        }

    # ------------------ HELPER METHODS ------------------ #

    def _build_explanation_prompt(
        self,
        question: str,
        tool_results: Dict[str, Any],
        rag_context: Optional[str]
    ) -> str:
        prompt = (
            "You are a precise, professional AI Financial Statement Analyst.\n"
            "CRITICAL PRINCIPLE: Never invent or hallucinate amounts, dates, or balances.\n"
            "All financial calculations were precomputed deterministically by verified tools.\n"
            "Only cite numbers, merchants, and dates directly present in the Verified Tool Results below.\n\n"
            f"User Question: {question}\n\n"
            f"Verified Tool Results:\n{json.dumps(tool_results, indent=2, default=str)}\n"
        )
        if rag_context:
            prompt += f"\nStatement Document Context:\n{rag_context}\n"

        prompt += (
            "\nProvide a clear, structured, and helpful explanation directly answering the user's question. "
            "Use bullet points and bold amounts for clarity."
        )
        return prompt

    def _call_llm_or_fallback(self, prompt: str, tool_results: Dict[str, Any], question: str) -> str:
        # Try configured LLM
        if settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
            try:
                from google import genai
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                resp = client.models.generate_content(
                    model=settings.GEMINI_MODEL_NAME,
                    contents=prompt
                )
                if resp.text:
                    return resp.text.strip()
            except Exception as e:
                logger.warning(f"Gemini API call failed, falling back to deterministic explanation: {e}")

        elif settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                resp = client.chat.completions.create(
                    model=settings.OPENAI_MODEL_NAME,
                    messages=[
                        {"role": "system", "content": "You are a helpful financial analyst."},
                        {"role": "user", "content": prompt}
                    ]
                )
                if resp.choices[0].message.content:
                    return resp.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"OpenAI API call failed, falling back to deterministic explanation: {e}")

        # Deterministic Explainer Fallback (works offline, guarantees 100% accuracy and zero hallucination)
        return self._deterministic_template_explainer(tool_results, question)

    def _deterministic_template_explainer(self, tool_results: Dict[str, Any], question: str) -> str:
        """High-quality deterministic explanation synthesizer when live external LLM is not configured."""
        lines = []

        if "get_total_credits" in tool_results and "get_total_debits" in tool_results:
            cr = tool_results["get_total_credits"]
            dr = tool_results["get_total_debits"]
            net = round(cr.get("total_credits", 0.0) - dr.get("total_debits", 0.0), 2)
            lines.append("### Financial Totals Summary")
            lines.append(f"- **Total Credits (Income/Deposits)**: ${cr.get('total_credits', 0.0):,.2f} ({cr.get('count', 0)} transactions)")
            lines.append(f"- **Total Debits (Spending/Withdrawals)**: ${dr.get('total_debits', 0.0):,.2f} ({dr.get('count', 0)} transactions)")
            lines.append(f"- **Net Cash Flow**: ${net:,.2f}")
            return "\n".join(lines)

        if "get_total_credits" in tool_results:
            cr = tool_results["get_total_credits"]
            lines.append(f"### Total Credits\n- **Total Deposits Received**: ${cr.get('total_credits', 0.0):,.2f} across {cr.get('count', 0)} transactions.")

        if "get_total_debits" in tool_results:
            dr = tool_results["get_total_debits"]
            lines.append(f"### Total Debits\n- **Total Amount Spent**: ${dr.get('total_debits', 0.0):,.2f} across {dr.get('count', 0)} transactions.")

        if "get_monthly_summary" in tool_results:
            m_res = tool_results["get_monthly_summary"]
            lines.append("### Monthly Financial Summary")
            for m in m_res.get("months", []):
                lines.append(f"- **{m['month_label']}**: Spent **${m['total_debits']:,.2f}**, Received **${m['total_credits']:,.2f}** (Net: **${m['net_cash_flow']:,.2f}**)")

        if "get_merchant_spending" in tool_results:
            m_data = tool_results["get_merchant_spending"]
            if "searched_merchant" in m_data:
                lines.append(f"### Spending with {m_data['searched_merchant']}")
                lines.append(f"- **Total Spent**: ${m_data['total_spent']:,.2f} across {m_data['count']} transactions.")
            elif "ranked_merchants" in m_data:
                lines.append("### Top Spending by Merchant")
                for item in m_data["ranked_merchants"][:5]:
                    lines.append(f"- **{item['merchant']}**: ${item['total_spent']:,.2f} ({item['count']} transactions)")

        if "get_category_spending" in tool_results:
            c_data = tool_results["get_category_spending"]
            lines.append("### Spending by Category")
            for item in c_data.get("categories", [])[:5]:
                lines.append(f"- **{item['category']}**: ${item['total_spent']:,.2f} ({item.get('percentage_of_spending', 0)}%)")

        if "get_money_received_sources" in tool_results:
            s_data = tool_results["get_money_received_sources"]
            lines.append(f"### Income & Credit Sources (${s_data.get('total_credits_received', 0.0):,.2f} total)")
            for item in s_data.get("credit_sources", [])[:5]:
                lines.append(f"- **{item['source']}**: ${item['total_received']:,.2f} ({item['count']} credits)")

        if "get_highest_credit" in tool_results:
            hc = tool_results["get_highest_credit"]
            lines.append(f"### Highest Credit\n- **Amount**: ${hc.get('amount', 0.0):,.2f}\n- **Source**: {hc.get('merchant')}\n- **Date**: {hc.get('date')}\n- **Description**: {hc.get('description')}")

        if "get_highest_debit" in tool_results:
            hd = tool_results["get_highest_debit"]
            lines.append(f"### Highest Debit\n- **Amount**: ${hd.get('amount', 0.0):,.2f}\n- **Merchant**: {hd.get('merchant')}\n- **Date**: {hd.get('date')}\n- **Description**: {hd.get('description')}")

        if "get_top_transactions" in tool_results:
            tt = tool_results["get_top_transactions"]
            lines.append(f"### Top {tt.get('count_returned')} Transactions")
            for t in tt.get("transactions", []):
                lines.append(f"- **{t['date']}** | **{t['merchant']}** | **${t['amount']:,.2f}** ({t['transaction_type']}) - {t['description']}")

        if "get_recurring_transactions" in tool_results:
            rec = tool_results["get_recurring_transactions"]
            lines.append(f"### Recurring Expenses & Subscriptions (Estimated ${rec.get('estimated_recurring_monthly', 0.0):,.2f}/month)")
            for item in rec.get("recurring_transactions", [])[:5]:
                lines.append(f"- **{item['merchant']}**: ${item['recurring_amount']:,.2f} ({item['frequency_count']} occurrences, {item['category']})")

        if "get_balance_summary" in tool_results:
            bs = tool_results["get_balance_summary"]
            lines.append("### Balance & Cash Flow Trajectory")
            if bs.get("opening_balance") is not None:
                lines.append(f"- **Opening Balance**: ${bs['opening_balance']:,.2f}")
            if bs.get("closing_balance") is not None:
                lines.append(f"- **Closing Balance**: ${bs['closing_balance']:,.2f}")
            lines.append(f"- **Net Cash Flow**: ${bs.get('net_flow', 0.0):,.2f}")

        if "get_transaction_count" in tool_results:
            tc = tool_results["get_transaction_count"]
            lines.append(f"### Transaction Counts\n- **Total Transactions**: {tc.get('total_transactions', 0)}\n- **Credits**: {tc.get('credit_count', 0)}\n- **Debits**: {tc.get('debit_count', 0)}")

        if "search_statement_text" in tool_results:
            rag = tool_results["search_statement_text"]
            lines.append(f"### Relevant Statement Notes ({rag.get('results_count', 0)} chunks found)")
            for c in rag.get("retrieved_chunks", []):
                lines.append(f"> {c['text'][:200]}...")

        if not lines:
            lines.append("Analysis completed. Please view the calculation results for detailed figures.")

        return "\n\n".join(lines)


orchestrator = FinancialAgentOrchestrator()
