"""Deterministic financial analytics engine."""

from datetime import date
from typing import List, Dict, Any, Optional
from collections import defaultdict

from app.models.transaction import NormalizedTransaction, TransactionType, FinancialSummary
from app.services.categorizer import CategorizerService


class FinancialAnalyticsEngine:
    """Deterministic analytics engine performing mathematical calculations over NormalizedTransaction sets."""

    def __init__(self, transactions: List[NormalizedTransaction]):
        self.transactions = transactions

    def get_total_credits(self) -> Dict[str, Any]:
        credits = [t for t in self.transactions if t.transaction_type == TransactionType.CREDIT]
        total = round(sum(t.amount for t in credits), 2)
        return {
            "total_credits": total,
            "count": len(credits),
            "currency": "USD"
        }

    def get_total_debits(self) -> Dict[str, Any]:
        debits = [t for t in self.transactions if t.transaction_type == TransactionType.DEBIT]
        total = round(sum(t.amount for t in debits), 2)
        return {
            "total_debits": total,
            "count": len(debits),
            "currency": "USD"
        }

    def get_credit_count(self) -> Dict[str, Any]:
        count = sum(1 for t in self.transactions if t.transaction_type == TransactionType.CREDIT)
        return {"credit_count": count}

    def get_debit_count(self) -> Dict[str, Any]:
        count = sum(1 for t in self.transactions if t.transaction_type == TransactionType.DEBIT)
        return {"debit_count": count}

    def get_transaction_count(self) -> Dict[str, Any]:
        credits = sum(1 for t in self.transactions if t.transaction_type == TransactionType.CREDIT)
        debits = sum(1 for t in self.transactions if t.transaction_type == TransactionType.DEBIT)
        return {
            "total_transactions": len(self.transactions),
            "credit_count": credits,
            "debit_count": debits
        }

    def get_highest_credit(self) -> Dict[str, Any]:
        credits = [t for t in self.transactions if t.transaction_type == TransactionType.CREDIT]
        if not credits:
            return {"highest_credit": None, "message": "No credit transactions found."}
        highest = max(credits, key=lambda t: t.amount)
        return {
            "highest_credit": highest.model_dump(),
            "amount": highest.amount,
            "merchant": highest.merchant,
            "date": highest.date.isoformat(),
            "description": highest.description
        }

    def get_highest_debit(self) -> Dict[str, Any]:
        debits = [t for t in self.transactions if t.transaction_type == TransactionType.DEBIT]
        if not debits:
            return {"highest_debit": None, "message": "No debit transactions found."}
        highest = max(debits, key=lambda t: t.amount)
        return {
            "highest_debit": highest.model_dump(),
            "amount": highest.amount,
            "merchant": highest.merchant,
            "date": highest.date.isoformat(),
            "description": highest.description
        }

    def get_transactions_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        filtered = self.transactions

        if start_date:
            try:
                s_dt = date.fromisoformat(start_date)
                filtered = [t for t in filtered if t.date >= s_dt]
            except ValueError:
                pass

        if end_date:
            try:
                e_dt = date.fromisoformat(end_date)
                filtered = [t for t in filtered if t.date <= e_dt]
            except ValueError:
                pass

        total_cr = round(sum(t.amount for t in filtered if t.transaction_type == TransactionType.CREDIT), 2)
        total_dr = round(sum(t.amount for t in filtered if t.transaction_type == TransactionType.DEBIT), 2)

        return {
            "start_date": start_date,
            "end_date": end_date,
            "count": len(filtered),
            "total_credits": total_cr,
            "total_debits": total_dr,
            "net_flow": round(total_cr - total_dr, 2),
            "transactions": [t.model_dump() for t in filtered]
        }

    def get_monthly_summary(self, month: Optional[int] = None, year: Optional[int] = None) -> Dict[str, Any]:
        """Calculates monthly breakdown of spending and income."""
        grouped: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "month_label": "",
            "year": 0,
            "month": 0,
            "total_credits": 0.0,
            "total_debits": 0.0,
            "net_cash_flow": 0.0,
            "credit_count": 0,
            "debit_count": 0,
            "total_transactions": 0
        })

        for t in self.transactions:
            if year and t.date.year != year:
                continue
            if month and t.date.month != month:
                continue

            key = f"{t.date.year:04d}-{t.date.month:02d}"
            item = grouped[key]
            item["month_label"] = t.date.strftime("%B %Y")
            item["year"] = t.date.year
            item["month"] = t.date.month
            item["total_transactions"] += 1

            if t.transaction_type == TransactionType.CREDIT:
                item["total_credits"] = round(item["total_credits"] + t.amount, 2)
                item["credit_count"] += 1
            else:
                item["total_debits"] = round(item["total_debits"] + t.amount, 2)
                item["debit_count"] += 1

            item["net_cash_flow"] = round(item["total_credits"] - item["total_debits"], 2)

        sorted_months = [grouped[k] for k in sorted(grouped.keys())]

        return {
            "months": sorted_months,
            "filter_month": month,
            "filter_year": year,
            "months_counted": len(sorted_months)
        }

    def get_merchant_spending(self, merchant_name: Optional[str] = None) -> Dict[str, Any]:
        """Calculates total money spent per merchant or for a specific merchant."""
        debits = [t for t in self.transactions if t.transaction_type == TransactionType.DEBIT]

        if merchant_name:
            clean_query = merchant_name.lower().strip()
            matched = [
                t for t in debits
                if clean_query in t.merchant.lower() or clean_query in t.description.lower()
            ]
            total = round(sum(t.amount for t in matched), 2)
            return {
                "searched_merchant": merchant_name,
                "total_spent": total,
                "count": len(matched),
                "transactions": [t.model_dump() for t in matched]
            }

        # Aggregate across all merchants
        spending_by_merchant: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"total": 0.0, "count": 0})
        for t in debits:
            m = t.merchant
            spending_by_merchant[m]["total"] = round(spending_by_merchant[m]["total"] + t.amount, 2)
            spending_by_merchant[m]["count"] += 1

        ranked = [
            {"merchant": m, "total_spent": data["total"], "count": data["count"]}
            for m, data in spending_by_merchant.items()
        ]
        ranked.sort(key=lambda x: x["total_spent"], reverse=True)

        return {
            "total_merchants": len(ranked),
            "ranked_merchants": ranked
        }

    def get_category_spending(self, category_name: Optional[str] = None) -> Dict[str, Any]:
        """Calculates spending breakdown by category."""
        debits = [t for t in self.transactions if t.transaction_type == TransactionType.DEBIT]

        if category_name:
            query = category_name.lower().strip()
            matched = [t for t in debits if query in t.category.lower()]
            total = round(sum(t.amount for t in matched), 2)
            return {
                "category": category_name,
                "total_spent": total,
                "count": len(matched),
                "transactions": [t.model_dump() for t in matched]
            }

        spending_by_cat: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"total": 0.0, "count": 0})
        total_spending = sum(t.amount for t in debits)

        for t in debits:
            c = t.category
            spending_by_cat[c]["total"] = round(spending_by_cat[c]["total"] + t.amount, 2)
            spending_by_cat[c]["count"] += 1

        ranked = []
        for cat, data in spending_by_cat.items():
            pct = round((data["total"] / total_spending * 100), 1) if total_spending > 0 else 0.0
            ranked.append({
                "category": cat,
                "total_spent": data["total"],
                "count": data["count"],
                "percentage_of_spending": pct
            })

        ranked.sort(key=lambda x: x["total_spent"], reverse=True)
        return {
            "total_spending": round(total_spending, 2),
            "categories": ranked
        }

    def get_money_received_sources(self) -> Dict[str, Any]:
        """Identifies and summarizes sources of incoming funds/credits."""
        credits = [t for t in self.transactions if t.transaction_type == TransactionType.CREDIT]
        sources: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"total": 0.0, "count": 0})

        for t in credits:
            m = t.merchant if t.merchant != "Unknown" else t.description[:30]
            sources[m]["total"] = round(sources[m]["total"] + t.amount, 2)
            sources[m]["count"] += 1

        ranked = [
            {"source": m, "total_received": data["total"], "count": data["count"]}
            for m, data in sources.items()
        ]
        ranked.sort(key=lambda x: x["total_received"], reverse=True)
        total_received = round(sum(t.amount for t in credits), 2)

        return {
            "total_credits_received": total_received,
            "credit_sources": ranked,
            "credit_count": len(credits)
        }

    def get_money_sent_destinations(self) -> Dict[str, Any]:
        """Identifies and ranks top entities or destinations money was sent to."""
        return self.get_merchant_spending()

    def get_average_transaction(self, transaction_type: Optional[str] = None) -> Dict[str, Any]:
        if transaction_type and transaction_type.upper() == "CREDIT":
            txns = [t for t in self.transactions if t.transaction_type == TransactionType.CREDIT]
            avg = round(sum(t.amount for t in txns) / len(txns), 2) if txns else 0.0
            return {"type": "CREDIT", "average_amount": avg, "count": len(txns)}
        elif transaction_type and transaction_type.upper() == "DEBIT":
            txns = [t for t in self.transactions if t.transaction_type == TransactionType.DEBIT]
            avg = round(sum(t.amount for t in txns) / len(txns), 2) if txns else 0.0
            return {"type": "DEBIT", "average_amount": avg, "count": len(txns)}
        else:
            credits = [t for t in self.transactions if t.transaction_type == TransactionType.CREDIT]
            debits = [t for t in self.transactions if t.transaction_type == TransactionType.DEBIT]
            avg_cr = round(sum(t.amount for t in credits) / len(credits), 2) if credits else 0.0
            avg_dr = round(sum(t.amount for t in debits) / len(debits), 2) if debits else 0.0
            overall_avg = round(sum(t.amount for t in self.transactions) / len(self.transactions), 2) if self.transactions else 0.0
            return {
                "overall_average": overall_avg,
                "average_credit": avg_cr,
                "average_debit": avg_dr,
                "total_count": len(self.transactions)
            }

    def get_recurring_transactions(self) -> Dict[str, Any]:
        recurring = CategorizerService.detect_recurring_transactions(self.transactions)
        total_recurring_monthly = round(sum(r["recurring_amount"] for r in recurring), 2)
        return {
            "recurring_count": len(recurring),
            "estimated_recurring_monthly": total_recurring_monthly,
            "recurring_transactions": recurring
        }

    def get_balance_summary(self) -> Dict[str, Any]:
        """Calculates opening and closing balances, net flow, and balance trajectory."""
        with_balance = [t for t in self.transactions if t.balance is not None]
        opening_balance = with_balance[0].balance if with_balance else None
        closing_balance = with_balance[-1].balance if with_balance else None

        total_cr = round(sum(t.amount for t in self.transactions if t.transaction_type == TransactionType.CREDIT), 2)
        total_dr = round(sum(t.amount for t in self.transactions if t.transaction_type == TransactionType.DEBIT), 2)
        net_flow = round(total_cr - total_dr, 2)

        return {
            "opening_balance": opening_balance,
            "closing_balance": closing_balance,
            "total_credits": total_cr,
            "total_debits": total_dr,
            "net_flow": net_flow,
            "transactions_tracked": len(self.transactions)
        }

    def get_top_transactions(
        self,
        n: int = 10,
        transaction_type: Optional[str] = None,
        sort_by: str = "amount"
    ) -> Dict[str, Any]:
        """Ranks top transactions deterministically."""
        txns = self.transactions
        if transaction_type:
            ttype = TransactionType.CREDIT if transaction_type.upper() == "CREDIT" else TransactionType.DEBIT
            txns = [t for t in txns if t.transaction_type == ttype]

        sorted_txns = sorted(txns, key=lambda t: t.amount, reverse=True)[:n]
        return {
            "top_n": n,
            "filter_type": transaction_type,
            "count_returned": len(sorted_txns),
            "transactions": [t.model_dump() for t in sorted_txns]
        }

    def compute_summary(self) -> FinancialSummary:
        """Builds a comprehensive FinancialSummary model."""
        credits = [t for t in self.transactions if t.transaction_type == TransactionType.CREDIT]
        debits = [t for t in self.transactions if t.transaction_type == TransactionType.DEBIT]

        total_cr = round(sum(t.amount for t in credits), 2)
        total_dr = round(sum(t.amount for t in debits), 2)

        with_balance = [t for t in self.transactions if t.balance is not None]

        highest_cr = max(credits, key=lambda t: t.amount) if credits else None
        highest_dr = max(debits, key=lambda t: t.amount) if debits else None

        return FinancialSummary(
            total_credits=total_cr,
            total_debits=total_dr,
            net_cash_flow=round(total_cr - total_dr, 2),
            credit_count=len(credits),
            debit_count=len(debits),
            transaction_count=len(self.transactions),
            start_date=self.transactions[0].date.isoformat() if self.transactions else None,
            end_date=self.transactions[-1].date.isoformat() if self.transactions else None,
            start_balance=with_balance[0].balance if with_balance else None,
            end_balance=with_balance[-1].balance if with_balance else None,
            average_credit=round(total_cr / len(credits), 2) if credits else 0.0,
            average_debit=round(total_dr / len(debits), 2) if debits else 0.0,
            highest_credit=highest_cr,
            highest_debit=highest_dr
        )
