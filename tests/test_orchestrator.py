"""Unit tests for LangGraph orchestrator."""

import pytest
from datetime import date
from app.models.transaction import NormalizedTransaction, TransactionType
from app.agents.orchestrator import orchestrator


@pytest.fixture
def transactions():
    return [
        NormalizedTransaction(
            transaction_id="t1",
            date=date(2024, 1, 2),
            description="Payroll",
            merchant="Acme Corp",
            transaction_type=TransactionType.CREDIT,
            amount=5000.00,
            balance=5000.00,
            category="Salary / Income",
            source="test"
        ),
        NormalizedTransaction(
            transaction_id="t2",
            date=date(2024, 1, 5),
            description="Amazon Order",
            merchant="Amazon",
            transaction_type=TransactionType.DEBIT,
            amount=150.00,
            balance=4850.00,
            category="Shopping & Retail",
            source="test"
        ),
        NormalizedTransaction(
            transaction_id="t3",
            date=date(2024, 1, 10),
            description="Starbucks Coffee",
            merchant="Starbucks",
            transaction_type=TransactionType.DEBIT,
            amount=15.00,
            balance=4835.00,
            category="Food & Dining",
            source="test"
        )
    ]


def test_orchestrator_total_credits_and_debits(transactions):
    resp = orchestrator.ask("What is my total credit and debit?", transactions)
    assert "get_total_credits" in resp.tools_used
    assert "get_total_debits" in resp.tools_used
    assert resp.calculation_results["get_total_credits"]["total_credits"] == 5000.00
    assert resp.calculation_results["get_total_debits"]["total_debits"] == 165.00
    assert "5,000.00" in resp.answer or "5000" in resp.answer
    assert resp.validation.is_valid is True


def test_orchestrator_merchant_spending(transactions):
    resp = orchestrator.ask("How much did I spend on Amazon?", transactions)
    assert "get_merchant_spending" in resp.tools_used
    assert resp.calculation_results["get_merchant_spending"]["total_spent"] == 150.00
    assert "Amazon" in resp.answer
    assert "150.00" in resp.answer


def test_orchestrator_where_did_money_go(transactions):
    resp = orchestrator.ask("Where did most of my money go?", transactions)
    assert any(t in resp.tools_used for t in ["get_category_spending", "get_merchant_spending"])
    assert resp.validation.is_valid is True
