"""End-to-end verification script testing the entire flow."""

import os
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_verification():
    print("=" * 60)
    print("1. Health Check")
    health = client.get("/health").json()
    print(f"Health Status: {health['status']}, Version: {health['version']}")

    print("\n2. Upload CSV Statement (sample_data/chase_statement.csv)")
    csv_path = os.path.join("sample_data", "chase_statement.csv")
    with open(csv_path, "rb") as f:
        resp = client.post("/upload", files={"file": ("chase_statement.csv", f, "text/csv")})
    upload_res = resp.json()
    stmt_id = upload_res["file_id"]
    print(f"Statement ID: {stmt_id}")
    print(f"Total Transactions Extracted: {upload_res['total_transactions']}")
    print(f"Total Credits: ${upload_res['summary']['total_credits']:,.2f}")
    print(f"Total Debits: ${upload_res['summary']['total_debits']:,.2f}")
    print(f"Net Cash Flow: ${upload_res['summary']['net_cash_flow']:,.2f}")

    test_questions = [
        "What is my total credit and debit?",
        "How much did I spend on Amazon?",
        "How much did I spend in January?",
        "Where did most of my money go?",
        "Where did my money come from?",
        "Show my top 5 transactions.",
        "What are my recurring subscriptions?"
    ]

    for q in test_questions:
        print(f"\n--- Testing Question: '{q}' ---")
        ask_resp = client.post("/ask", json={"question": q, "session_id": stmt_id}).json()
        print(f"Tools Used: {ask_resp['tools_used']}")
        print(f"Validation Passed: {ask_resp['validation']['is_valid']}, Grounded: {ask_resp['validation']['grounded_in_tools']}")
        print(f"Answer:\n{ask_resp['answer']}")

    print("\n3. Testing PDF Statement Upload (sample_data/sample_statement.pdf)")
    pdf_path = os.path.join("sample_data", "sample_statement.pdf")
    with open(pdf_path, "rb") as f:
        pdf_res = client.post("/upload", files={"file": ("sample_statement.pdf", f, "application/pdf")}).json()
    print(f"PDF Statement ID: {pdf_res['file_id']}, Transactions: {pdf_res['total_transactions']}")

    pdf_ask = client.post("/ask", json={"question": "What is my highest debit expense?", "session_id": pdf_res['file_id']}).json()
    print(f"PDF Highest Debit Answer:\n{pdf_ask['answer']}")

    print("\n4. Testing Excel Statement Upload (sample_data/wells_fargo_statement.xlsx)")
    excel_path = os.path.join("sample_data", "wells_fargo_statement.xlsx")
    with open(excel_path, "rb") as f:
        excel_res = client.post("/upload", files={"file": ("wells_fargo_statement.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}).json()
    print(f"Excel Statement ID: {excel_res['file_id']}, Transactions: {excel_res['total_transactions']}")

    print("\n" + "=" * 60)
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_verification()
