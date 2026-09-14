"""Integration tests for FastAPI endpoints."""

import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_upload_and_ask_csv():
    # 1. Test Upload CSV
    csv_path = os.path.join("sample_data", "chase_statement.csv")
    with open(csv_path, "rb") as f:
        files = {"file": ("chase_statement.csv", f, "text/csv")}
        upload_resp = client.post("/upload", files=files)

    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    statement_id = upload_data["file_id"]
    assert upload_data["total_transactions"] >= 20
    assert upload_data["summary"]["total_credits"] > 0
    assert upload_data["summary"]["total_debits"] > 0

    # 2. Test Ask endpoint - Total credit and debit
    ask_payload = {
        "question": "What is my total credit and debit?",
        "session_id": statement_id
    }
    ask_resp = client.post("/ask", json=ask_payload)
    assert ask_resp.status_code == 200
    ask_data = ask_resp.json()
    assert "get_total_credits" in ask_data["tools_used"]
    assert "get_total_debits" in ask_data["tools_used"]
    assert ask_data["validation"]["is_valid"] is True

    # 3. Test Ask for merchant spending
    ask_amz = client.post("/ask", json={"question": "How much did I spend on Amazon?", "session_id": statement_id})
    assert ask_amz.status_code == 200
    assert "get_merchant_spending" in ask_amz.json()["tools_used"]

    # 4. Test Ask for monthly summary
    ask_jan = client.post("/ask", json={"question": "How much did I spend in January?", "session_id": statement_id})
    assert ask_jan.status_code == 200
    assert "get_monthly_summary" in ask_jan.json()["tools_used"]

    # 5. Test Ask for recurring subscriptions
    ask_rec = client.post("/ask", json={"question": "What are my recurring subscriptions?", "session_id": statement_id})
    assert ask_rec.status_code == 200
    assert "get_recurring_transactions" in ask_rec.json()["tools_used"]

    # 6. Test Transactions endpoint with filter
    txns_resp = client.get(f"/transactions?statement_id={statement_id}&limit=5")
    assert txns_resp.status_code == 200
    txns_data = txns_resp.json()
    assert len(txns_data["transactions"]) <= 5
    assert txns_data["total"] >= 20

    # 7. Test Summary endpoint
    summary_resp = client.get(f"/summary?statement_id={statement_id}")
    assert summary_resp.status_code == 200
    sum_data = summary_resp.json()
    assert sum_data["total_credits"] == upload_data["summary"]["total_credits"]
    assert sum_data["total_debits"] == upload_data["summary"]["total_debits"]


def test_upload_and_ask_excel():
    excel_path = os.path.join("sample_data", "wells_fargo_statement.xlsx")
    with open(excel_path, "rb") as f:
        files = {"file": ("wells_fargo_statement.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        upload_resp = client.post("/upload", files=files)

    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    statement_id = upload_data["file_id"]
    assert upload_data["total_transactions"] == 10

    # Ask where did most of my money go
    ask_resp = client.post("/ask", json={"question": "Where did most of my money go?", "session_id": statement_id})
    assert ask_resp.status_code == 200
    assert any(t in ask_resp.json()["tools_used"] for t in ["get_category_spending", "get_merchant_spending"])


def test_upload_and_ask_pdf():
    pdf_path = os.path.join("sample_data", "sample_statement.pdf")
    with open(pdf_path, "rb") as f:
        files = {"file": ("sample_statement.pdf", f, "application/pdf")}
        upload_resp = client.post("/upload", files=files)

    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    statement_id = upload_data["file_id"]
    assert upload_data["total_transactions"] >= 7

    # Ask for highest debit
    ask_resp = client.post("/ask", json={"question": "What is my highest debit expense?", "session_id": statement_id})
    assert ask_resp.status_code == 200
    assert "get_highest_debit" in ask_resp.json()["tools_used"]
    assert ask_resp.json()["calculation_results"]["get_highest_debit"]["amount"] == 1600.00
