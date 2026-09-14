"""Unit tests for deterministic financial analytics engine."""

import pytest
from datetime import date
from app.models.transaction import NormalizedTransaction, TransactionType
from app.analytics.engine import FinancialAnalyticsEngine
from app.tools.analytics_tools import registry


@pytest.fixture
def sample_transactions():
    return [
        NormalizedTransaction(
            transaction_id="t1",
            date=date(2024, 1, 2),
            description="Payroll Deposit",
            merchant="Acme Corp",
            transaction_type=TransactionType.CREDIT,
            amount=4500.00,
            balance=4500.00,
            category="Salary / Income",
            source="test"
        ),
        NormalizedTransaction(
            transaction_id="t2",
            date=date(2024, 1, 5),
            description="Rent Payment",
            merchant="Apartment Co",
            transaction_type=TransactionType.DEBIT,
            amount=1850.00,
            balance=2650.00,
            category="Rent & Housing",
            source="test"
        ),
        NormalizedTransaction(
            transaction_id="t3",
            date=date(2024, 1, 10),
            description="Amazon Order",
            merchant="Amazon",
            transaction_type=TransactionType.DEBIT,
            amount=100.00,
            balance=2550.00,
            category="Shopping & Retail",
            source="test"
        ),
        NormalizedTransaction(
            transaction_id="t4",
            date=date(2024, 1, 15),
            description="Netflix Subscription",
            merchant="Netflix",
            transaction_type=TransactionType.DEBIT,
            amount=20.00,
            balance=2530.00,
            category="Subscriptions & Media",
            source="test"
        ),
        NormalizedTransaction(
            transaction_id="t5",
            date=date(2024, 2, 2),
            description="Payroll Deposit",
            merchant="Acme Corp",
            transaction_type=TransactionType.CREDIT,
            amount=4500.00,
            balance=7030.00,
            category="Salary / Income",
            source="test"
        ),
        NormalizedTransaction(
            transaction_id="t6",
            date=date(2024, 2, 15),
            description="Netflix Subscription",
            merchant="Netflix",
            transaction_type=TransactionType.DEBIT,
            amount=20.00,
            balance=7010.00,
            category="Subscriptions & Media",
            source="test"
        ),
        NormalizedTransaction(
            transaction_id="t7",
            date=date(2024, 2, 18),
            description="Amazon Books",
            merchant="Amazon",
            transaction_type=TransactionType.DEBIT,
            amount=50.00,
            balance=6960.00,
            category="Shopping & Retail",
            source="test"
        )
    ]


def test_totals_and_counts(sample_transactions):
    engine = FinancialAnalyticsEngine(sample_transactions)

    cr = engine.get_total_credits()
    assert cr["total_credits"] == 9000.00
    assert cr["count"] == 2

    dr = engine.get_total_debits()
    assert dr["total_debits"] == 2040.00
    assert dr["count"] == 5

    counts = engine.get_transaction_count()
    assert counts["total_transactions"] == 7
    assert counts["credit_count"] == 2
    assert counts["debit_count"] == 5


def test_highest_credit_and_debit(sample_transactions):
    engine = FinancialAnalyticsEngine(sample_transactions)

    hc = engine.get_highest_credit()
    assert hc["amount"] == 4500.00
    assert hc["merchant"] == "Acme Corp"

    hd = engine.get_highest_debit()
    assert hd["amount"] == 1850.00
    assert hd["merchant"] == "Apartment Co"


def test_merchant_spending(sample_transactions):
    engine = FinancialAnalyticsEngine(sample_transactions)

    # Specific merchant
    amz = engine.get_merchant_spending("Amazon")
    assert amz["total_spent"] == 150.00
    assert amz["count"] == 2

    # All merchants ranked
    all_m = engine.get_merchant_spending()
    assert all_m["ranked_merchants"][0]["merchant"] == "Apartment Co"
    assert all_m["ranked_merchants"][0]["total_spent"] == 1850.00


def test_monthly_summary(sample_transactions):
    engine = FinancialAnalyticsEngine(sample_transactions)

    monthly = engine.get_monthly_summary()
    assert len(monthly["months"]) == 2

    # Jan 2024
    jan = monthly["months"][0]
    assert jan["year"] == 2024
    assert jan["month"] == 1
    assert jan["total_credits"] == 4500.00
    assert jan["total_debits"] == 1970.00
    assert jan["net_cash_flow"] == 2530.00

    # Specific month filter
    feb_only = engine.get_monthly_summary(month=2)
    assert len(feb_only["months"]) == 1
    assert feb_only["months"][0]["month"] == 2


def test_category_spending(sample_transactions):
    engine = FinancialAnalyticsEngine(sample_transactions)

    cat_res = engine.get_category_spending()
    assert cat_res["total_spending"] == 2040.00
    assert len(cat_res["categories"]) >= 3


def test_recurring_transactions(sample_transactions):
    engine = FinancialAnalyticsEngine(sample_transactions)

    rec = engine.get_recurring_transactions()
    assert rec["recurring_count"] >= 1
    netflix = [r for r in rec["recurring_transactions"] if r["merchant"] == "Netflix"]
    assert len(netflix) == 1
    assert netflix[0]["frequency_count"] == 2
    assert netflix[0]["recurring_amount"] == 20.00


def test_balance_summary(sample_transactions):
    engine = FinancialAnalyticsEngine(sample_transactions)

    bal = engine.get_balance_summary()
    assert bal["opening_balance"] == 4500.00
    assert bal["closing_balance"] == 6960.00
    assert bal["net_flow"] == 6960.00


def test_tool_registry_dispatch(sample_transactions):
    engine = FinancialAnalyticsEngine(sample_transactions)

    res = registry.execute("get_merchant_spending", engine, merchant_name="Netflix")
    assert res["total_spent"] == 40.00
    assert res["count"] == 2
