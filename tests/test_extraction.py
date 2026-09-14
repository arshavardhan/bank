"""Unit tests for document extraction from CSV, Excel, and PDF."""

import os
import pytest
from app.extraction.csv_excel_extractor import CsvExcelExtractor
from app.extraction.pdf_extractor import PdfExtractor


def test_csv_extraction():
    extractor = CsvExcelExtractor()
    csv_path = os.path.join("sample_data", "chase_statement.csv")
    with open(csv_path, "rb") as f:
        content = f.read()

    data = extractor.extract(content, "chase_statement.csv")
    assert len(data.dataframes) == 1
    df = data.dataframes[0]
    assert len(df) >= 20
    assert "Description" in df.columns or "description" in [c.lower() for c in df.columns]


def test_excel_extraction():
    extractor = CsvExcelExtractor()
    excel_path = os.path.join("sample_data", "wells_fargo_statement.xlsx")
    with open(excel_path, "rb") as f:
        content = f.read()

    data = extractor.extract(content, "wells_fargo_statement.xlsx")
    assert len(data.dataframes) == 1
    df = data.dataframes[0]
    assert len(df) == 10
    assert any("amount" in c.lower() for c in df.columns)


def test_pdf_extraction():
    extractor = PdfExtractor()
    pdf_path = os.path.join("sample_data", "sample_statement.pdf")
    with open(pdf_path, "rb") as f:
        content = f.read()

    data = extractor.extract(content, "sample_statement.pdf")
    assert len(data.dataframes) >= 1
    assert "FIRST NATIONAL BANK" in data.raw_text
    assert "Account Fees" in data.raw_text
