"""Unit tests for transaction normalization layer."""

import pytest
import pandas as pd
from datetime import date
from app.extraction.normalizer import TransactionNormalizer
from app.models.transaction import TransactionType
from app.services.categorizer import CategorizerService


def test_normalize_chase_format():
    """Test normalizing a CSV with separate Debit and Credit columns."""
    df = pd.DataFrame([
        {"Transaction Date": "2024-01-02", "Description": "ACH DEPOSIT: ACME CORP PAYROLL", "Debit": "", "Credit": "4500.00", "Balance": "4500.00"},
        {"Transaction Date": "2024-01-03", "Description": "RENT PAYMENT - MAIN ST APARTMENTS", "Debit": "1850.00", "Credit": "", "Balance": "2650.00"},
        {"Transaction Date": "2024-01-08", "Description": "AMAZON.COM*ORDER 204-9281", "Debit": "89.99", "Credit": "", "Balance": "2560.01"}
    ])

    normalizer = TransactionNormalizer()
    txns, warnings = normalizer.normalize(df, source="test_chase.csv")

    assert len(txns) == 3
    # Check deposit
    assert txns[0].transaction_type == TransactionType.CREDIT
    assert txns[0].amount == 4500.00
    assert txns[0].balance == 4500.00
    assert txns[0].date == date(2024, 1, 2)
    assert txns[0].category == "Salary / Income"

    # Check rent debit
    assert txns[1].transaction_type == TransactionType.DEBIT
    assert txns[1].amount == 1850.00
    assert txns[1].balance == 2650.00
    assert txns[1].category == "Rent & Housing"

    # Check amazon debit
    assert txns[2].transaction_type == TransactionType.DEBIT
    assert txns[2].merchant == "Amazon"
    assert txns[2].amount == 89.99


def test_normalize_signed_amount_format():
    """Test normalizing a statement with single signed amount column (+ / -)."""
    df = pd.DataFrame([
        {"Date": "2024-03-01", "Narration": "SALARY DIRECT DEP", "Amount": "5000.00", "Balance": "5000.00"},
        {"Date": "2024-03-05", "Narration": "SAFEWAY GROCERY STORE", "Amount": "-120.50", "Balance": "4879.50"},
        {"Date": "2024-03-10", "Narration": "NETFLIX.COM PAYMENT", "Amount": "(19.99)", "Balance": "4859.51"}
    ])

    normalizer = TransactionNormalizer()
    txns, warnings = normalizer.normalize(df, source="test_signed.csv")

    assert len(txns) == 3
    assert txns[0].transaction_type == TransactionType.CREDIT
    assert txns[0].amount == 5000.00

    assert txns[1].transaction_type == TransactionType.DEBIT
    assert txns[1].amount == 120.50

    assert txns[2].transaction_type == TransactionType.DEBIT
    assert txns[2].amount == 19.99
    assert txns[2].merchant == "Netflix"


def test_merchant_cleaning():
    clean1 = CategorizerService.extract_clean_merchant("POS PURCHASE - AMAZON.COM*MBR 1234 SEATTLE WA")
    assert clean1 == "Amazon"

    clean2 = CategorizerService.extract_clean_merchant("STARBUCKS STORE #04822 SAN FRANCISCO CA")
    assert clean2 == "Starbucks"

    clean3 = CategorizerService.extract_clean_merchant("ACH DEPOSIT: GOOGLE PAYROLL")
    assert clean3 == "Google"
