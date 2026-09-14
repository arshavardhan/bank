"""Deterministic tool registry and definitions for financial queries."""

from typing import Dict, Any, Callable, Optional, List
from app.analytics.engine import FinancialAnalyticsEngine


class ToolRegistry:
    """Registry mapping tool names to execution functions with metadata."""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._descriptions: Dict[str, str] = {}

    def register(self, name: str, description: str):
        def decorator(fn: Callable):
            self._tools[name] = fn
            self._descriptions[name] = description
            return fn
        return decorator

    def get_tool(self, name: str) -> Optional[Callable]:
        return self._tools.get(name)

    def get_all_descriptions(self) -> Dict[str, str]:
        return self._descriptions.copy()

    def execute(self, name: str, engine: FinancialAnalyticsEngine, **kwargs) -> Dict[str, Any]:
        fn = self.get_tool(name)
        if not fn:
            raise ValueError(f"Unknown tool: {name}")
        return fn(engine, **kwargs)


registry = ToolRegistry()


@registry.register("get_total_credits", "Calculate the total monetary sum of all deposits/credits received.")
def tool_total_credits(engine: FinancialAnalyticsEngine, **kwargs) -> Dict[str, Any]:
    return engine.get_total_credits()


@registry.register("get_total_debits", "Calculate the total monetary sum of all withdrawals/debits spent.")
def tool_total_debits(engine: FinancialAnalyticsEngine, **kwargs) -> Dict[str, Any]:
    return engine.get_total_debits()


@registry.register("get_credit_count", "Get the total count of credit/deposit transactions.")
def tool_credit_count(engine: FinancialAnalyticsEngine, **kwargs) -> Dict[str, Any]:
    return engine.get_credit_count()


@registry.register("get_debit_count", "Get the total count of debit/expense transactions.")
def tool_debit_count(engine: FinancialAnalyticsEngine, **kwargs) -> Dict[str, Any]:
    return engine.get_debit_count()


@registry.register("get_transaction_count", "Get total count of all transactions, credits, and debits.")
def tool_transaction_count(engine: FinancialAnalyticsEngine, **kwargs) -> Dict[str, Any]:
    return engine.get_transaction_count()


@registry.register("get_highest_credit", "Find the single largest deposit or credit transaction.")
def tool_highest_credit(engine: FinancialAnalyticsEngine, **kwargs) -> Dict[str, Any]:
    return engine.get_highest_credit()


@registry.register("get_highest_debit", "Find the single largest withdrawal, purchase, or debit transaction.")
def tool_highest_debit(engine: FinancialAnalyticsEngine, **kwargs) -> Dict[str, Any]:
    return engine.get_highest_debit()


@registry.register("get_transactions_by_date_range", "Filter transactions by start_date and end_date (YYYY-MM-DD).")
def tool_transactions_by_date_range(
    engine: FinancialAnalyticsEngine,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    return engine.get_transactions_by_date_range(start_date=start_date, end_date=end_date)


@registry.register("get_monthly_summary", "Get monthly breakdown of spending and income by month and year.")
def tool_monthly_summary(
    engine: FinancialAnalyticsEngine,
    month: Optional[int] = None,
    year: Optional[int] = None,
    **kwargs
) -> Dict[str, Any]:
    return engine.get_monthly_summary(month=month, year=year)


@registry.register("get_merchant_spending", "Get spending breakdown per merchant or query a specific merchant like Amazon, Starbucks, etc.")
def tool_merchant_spending(
    engine: FinancialAnalyticsEngine,
    merchant_name: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    return engine.get_merchant_spending(merchant_name=merchant_name)


@registry.register("get_category_spending", "Get spending breakdown by category (e.g. Groceries, Dining, Utilities) or query a specific category.")
def tool_category_spending(
    engine: FinancialAnalyticsEngine,
    category_name: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    return engine.get_category_spending(category_name=category_name)


@registry.register("get_money_received_sources", "Analyze where money came from, ranking all income and credit sources.")
def tool_money_received_sources(engine: FinancialAnalyticsEngine, **kwargs) -> Dict[str, Any]:
    return engine.get_money_received_sources()


@registry.register("get_money_sent_destinations", "Analyze where money went, ranking destinations and payees.")
def tool_money_sent_destinations(engine: FinancialAnalyticsEngine, **kwargs) -> Dict[str, Any]:
    return engine.get_money_sent_destinations()


@registry.register("get_average_transaction", "Calculate average transaction amount for credits, debits, or overall.")
def tool_average_transaction(
    engine: FinancialAnalyticsEngine,
    transaction_type: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    return engine.get_average_transaction(transaction_type=transaction_type)


@registry.register("get_recurring_transactions", "Detect recurring subscriptions, bills, and periodic charges.")
def tool_recurring_transactions(engine: FinancialAnalyticsEngine, **kwargs) -> Dict[str, Any]:
    return engine.get_recurring_transactions()


@registry.register("get_balance_summary", "Get opening balance, closing balance, net cash flow, and trend.")
def tool_balance_summary(engine: FinancialAnalyticsEngine, **kwargs) -> Dict[str, Any]:
    return engine.get_balance_summary()


@registry.register("get_top_transactions", "Retrieve top N highest transactions, optionally filtered by type.")
def tool_top_transactions(
    engine: FinancialAnalyticsEngine,
    n: int = 10,
    transaction_type: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    return engine.get_top_transactions(n=n, transaction_type=transaction_type)
