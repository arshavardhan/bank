"""Validation layer verifying mathematical consistency and ensuring LLM outputs are strictly grounded."""

import re
from typing import List, Dict, Any, Optional
from app.models.transaction import NormalizedTransaction, TransactionType, FinancialSummary
from app.models.schemas import ValidationInfo


class FinancialResultValidator:
    """Validates transaction integrity, mathematical consistency, and grounds LLM responses."""

    @classmethod
    def validate_transactions_integrity(cls, transactions: List[NormalizedTransaction]) -> Dict[str, Any]:
        flags: List[str] = []
        if not transactions:
            return {"is_valid": False, "flags": ["No transactions to validate."]}

        invalid_amounts = [t for t in transactions if t.amount <= 0]
        if invalid_amounts:
            flags.append(f"Found {len(invalid_amounts)} transactions with non-positive amounts.")

        unlabeled = [t for t in transactions if t.merchant == "Unknown Merchant" or not t.description]
        if unlabeled:
            flags.append(f"Flagged {len(unlabeled)} transactions with ambiguous or missing descriptions.")

        # Check balance continuity if available
        discrepancies = 0
        for i in range(1, len(transactions)):
            prev = transactions[i - 1]
            curr = transactions[i]
            if prev.balance is not None and curr.balance is not None:
                expected = (
                    prev.balance + curr.amount
                    if curr.transaction_type == TransactionType.CREDIT
                    else prev.balance - curr.amount
                )
                if abs(expected - curr.balance) > 0.05:
                    discrepancies += 1

        if discrepancies > 0:
            flags.append(f"Balance check: {discrepancies} consecutive transactions had balance delta discrepancies.")

        return {
            "is_valid": len(invalid_amounts) == 0,
            "transaction_count": len(transactions),
            "flags": flags
        }

    @classmethod
    def validate_calculation_consistency(cls, summary: FinancialSummary) -> ValidationInfo:
        flags: List[str] = []
        is_consistent = True

        # Check net cash flow math: credits - debits
        expected_net = round(summary.total_credits - summary.total_debits, 2)
        if abs(expected_net - summary.net_cash_flow) > 0.01:
            flags.append(f"Net cash flow mismatch: {summary.net_cash_flow} != expected {expected_net}")
            is_consistent = False

        # Check counts
        if (summary.credit_count + summary.debit_count) != summary.transaction_count:
            flags.append(f"Count mismatch: credits ({summary.credit_count}) + debits ({summary.debit_count}) != total ({summary.transaction_count})")
            is_consistent = False

        return ValidationInfo(
            is_valid=is_consistent,
            grounded_in_tools=True,
            claims_verified=True,
            consistency_passed=is_consistent,
            flags=flags
        )

    @classmethod
    def validate_llm_response(
        cls,
        llm_response: str,
        tool_results: Dict[str, Any]
    ) -> ValidationInfo:
        """Verifies that all significant numbers mentioned in the LLM response originate from the tool results."""
        flags: List[str] = []
        
        # Flatten all numerical values in tool_results to string representations
        tool_numbers = cls._extract_numbers_from_structure(tool_results)

        # Extract dollar figures and decimals from LLM response
        # Matches patterns like $1,234.56, 1234.56, 45.00
        llm_currency_matches = re.findall(r"\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})|\b[0-9]+\.[0-9]{1,2}\b)", llm_response)
        
        cleaned_llm_numbers = set()
        for match in llm_currency_matches:
            try:
                num = round(float(match.replace(",", "")), 2)
                # Ignore trivial digits like 0, 1, 2 (often bullet points)
                if num > 2:
                    cleaned_llm_numbers.add(num)
            except ValueError:
                pass

        unverified_numbers = []
        for num in cleaned_llm_numbers:
            # Check if num or close approximation is in tool_numbers
            matched = any(abs(num - t_num) < 0.05 for t_num in tool_numbers)
            if not matched:
                unverified_numbers.append(num)

        grounded = len(unverified_numbers) == 0
        if not grounded:
            flags.append(
                f"LLM response cited figures not present in tool calculations: {unverified_numbers}."
            )

        return ValidationInfo(
            is_valid=True,
            grounded_in_tools=grounded,
            claims_verified=grounded,
            consistency_passed=True,
            flags=flags
        )

    @classmethod
    def _extract_numbers_from_structure(cls, data: Any) -> List[float]:
        numbers: List[float] = []
        if isinstance(data, dict):
            for v in data.values():
                numbers.extend(cls._extract_numbers_from_structure(v))
        elif isinstance(data, list):
            for item in data:
                numbers.extend(cls._extract_numbers_from_structure(item))
        elif isinstance(data, (int, float)):
            numbers.append(round(float(data), 2))
        elif isinstance(data, str):
            # If string looks like a number
            clean = data.replace(",", "").replace("$", "").strip()
            try:
                numbers.append(round(float(clean), 2))
            except ValueError:
                pass
        return numbers
