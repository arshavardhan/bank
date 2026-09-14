"""Unit tests for the validation and anti-hallucination auditing layer."""

from datetime import date
from app.models.transaction import NormalizedTransaction, TransactionType, FinancialSummary
from app.validation.validator import FinancialResultValidator


def test_validate_calculation_consistency():
    valid_summary = FinancialSummary(
        total_credits=5000.00,
        total_debits=2000.00,
        net_cash_flow=3000.00,
        credit_count=2,
        debit_count=8,
        transaction_count=10
    )
    val = FinancialResultValidator.validate_calculation_consistency(valid_summary)
    assert val.is_valid is True
    assert val.consistency_passed is True
    assert len(val.flags) == 0

    # Inconsistent net cash flow
    bad_summary = FinancialSummary(
        total_credits=5000.00,
        total_debits=2000.00,
        net_cash_flow=4000.00,  # Should be 3000.00
        credit_count=2,
        debit_count=8,
        transaction_count=10
    )
    bad_val = FinancialResultValidator.validate_calculation_consistency(bad_summary)
    assert bad_val.is_valid is False
    assert any("Net cash flow mismatch" in f for f in bad_val.flags)


def test_validate_llm_response_grounded():
    tool_results = {
        "get_total_credits": {"total_credits": 4500.00, "count": 1},
        "get_total_debits": {"total_debits": 1850.00, "count": 1}
    }

    # Grounded response referencing the exact numbers
    good_response = "You received a total credit of $4,500.00 and your total debits were $1,850.00."
    val = FinancialResultValidator.validate_llm_response(good_response, tool_results)
    assert val.grounded_in_tools is True
    assert len(val.flags) == 0

    # Hallucinated response introducing an invented figure ($9,999.00)
    hallucinated_response = "You spent $1,850.00, and your estimated balance was $9,999.00."
    bad_val = FinancialResultValidator.validate_llm_response(hallucinated_response, tool_results)
    assert bad_val.grounded_in_tools is False
    assert any("not present in tool calculations" in f for f in bad_val.flags)
