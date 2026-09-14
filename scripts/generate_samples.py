"""Generate sample Excel and PDF bank statements for testing."""

import os
import pandas as pd
import fitz  # PyMuPDF

os.makedirs("sample_data", exist_ok=True)

# 1. Generate Excel Statement (Wells Fargo format with signed amount)
wf_data = {
    "Posting Date": [
        "2024-03-01", "2024-03-02", "2024-03-04", "2024-03-07", "2024-03-10",
        "2024-03-15", "2024-03-18", "2024-03-22", "2024-03-25", "2024-03-29"
    ],
    "Details / Narration": [
        "DIRECT DEP ACME CORP PAYROLL",
        "MORTGAGE PAYMENT WELLS FARGO HOME LOAN",
        "SAFEWAY STORE #1920 GROCERY",
        "AMAZON.COM RETAIL PURCHASE",
        "SHELL OIL 1092 FUEL",
        "NETFLIX.COM PAYMENT",
        "STARBUCKS COFFEE #102",
        "AT&T WIRELESS BILL",
        "TRADER JOE'S MARKET",
        "FREELANCE DESIGN CLIENT INVOICE #102"
    ],
    "Amount": [
        "5200.00",
        "-2100.00",
        "-135.40",
        "-78.50",
        "-52.00",
        "-19.99",
        "-8.50",
        "-85.00",
        "-112.30",
        "1450.00"
    ],
    "Running Balance": [
        "5200.00", "3100.00", "2964.60", "2886.10", "2834.10",
        "2814.11", "2805.61", "2720.61", "2608.31", "4058.31"
    ]
}

df_wf = pd.DataFrame(wf_data)
excel_path = os.path.join("sample_data", "wells_fargo_statement.xlsx")
df_wf.to_excel(excel_path, index=False, engine="openpyxl")
print(f"Generated {excel_path}")

# 2. Generate PDF Statement with PyMuPDF
doc = fitz.open()
page = doc.new_page(width=595, height=842)  # A4 size

# Title & metadata
page.insert_text(fitz.Point(50, 50), "FIRST NATIONAL BANK - MONTHLY STATEMENT", fontsize=16, fontname="helv", color=(0.1, 0.2, 0.5))
page.insert_text(fitz.Point(50, 75), "Account Number: 9876-5432-1098 | Statement Period: Jan 01, 2024 - Jan 31, 2024", fontsize=10, fontname="helv")
page.insert_text(fitz.Point(50, 95), "Customer Service: 1-800-555-0199 | Overdraft Policy: Standard $35 fee per occurrence.", fontsize=9, fontname="helv")

# Table Header
headers = ["Date", "Description", "Debit", "Credit", "Balance"]
x_positions = [50, 130, 340, 420, 500]
y = 130

# Draw table header
for x, h in zip(x_positions, headers):
    page.insert_text(fitz.Point(x, y), h, fontsize=10, fontname="helv", color=(0.2, 0.2, 0.2))

# Table rows
pdf_rows = [
    ("2024-01-02", "ACME PAYROLL DIRECT DEPOSIT", "", "4200.00", "4200.00"),
    ("2024-01-03", "RENT PAYMENT - APARTMENT 4B", "1600.00", "", "2600.00"),
    ("2024-01-06", "WHOLE FOODS GROCERIES", "124.50", "", "2475.50"),
    ("2024-01-10", "AMAZON.COM*PURCHASE", "59.99", "", "2415.51"),
    ("2024-01-14", "NETFLIX MONTHLY", "19.99", "", "2395.52"),
    ("2024-01-18", "ELECTRIC UTILITY PAYMENT", "89.40", "", "2306.12"),
    ("2024-01-22", "STARBUCKS STORE 12", "7.50", "", "2298.62"),
    ("2024-01-28", "ZELLE PAYMENT FROM SARAH", "", "150.00", "2448.62")
]

for row in pdf_rows:
    y += 24
    for x, val in zip(x_positions, row):
        page.insert_text(fitz.Point(x, y), val, fontsize=9, fontname="helv")

# Footnotes / Policy for RAG verification
y += 40
page.insert_text(fitz.Point(50, y), "IMPORTANT NOTICES & STATEMENT TERMS:", fontsize=10, fontname="helv", color=(0.1, 0.2, 0.5))
y += 18
page.insert_text(fitz.Point(50, y), "1. Account Fees: Monthly maintenance fee of $12 is waived with direct deposit of $500 or more.", fontsize=8, fontname="helv")
y += 14
page.insert_text(fitz.Point(50, y), "2. Dispute Policy: You must notify the bank within 60 days of this statement date for any errors.", fontsize=8, fontname="helv")

pdf_path = os.path.join("sample_data", "sample_statement.pdf")
doc.save(pdf_path)
doc.close()
print(f"Generated {pdf_path}")
