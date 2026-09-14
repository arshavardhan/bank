"""Generate a comprehensive 6-month realistic bank statement dataset."""

import os
import pandas as pd
from datetime import date, timedelta

os.makedirs("sample_data", exist_ok=True)

# 60 realistic transactions across Jan - Jun
transactions_data = [
    # --- January 2024 ---
    {"Date": "2024-01-02", "Description": "ACH DEPOSIT: ACME CORP BI-WEEKLY PAYROLL", "Category": "Salary / Income", "Debit": None, "Credit": 3750.00, "Balance": 6250.00},
    {"Date": "2024-01-03", "Description": "ONLINE TRANSFER - RENT TO HIGHLAND APARTMENTS", "Category": "Rent & Housing", "Debit": 1950.00, "Credit": None, "Balance": 4300.00},
    {"Date": "2024-01-04", "Description": "WHOLE FOODS MARKET #10424 GROCERY", "Category": "Groceries", "Debit": 138.45, "Credit": None, "Balance": 4161.55},
    {"Date": "2024-01-06", "Description": "STARBUCKS STORE #04822 COFFEE", "Category": "Food & Dining", "Debit": 6.85, "Credit": None, "Balance": 4154.70},
    {"Date": "2024-01-08", "Description": "AMAZON.COM*ORDER 204-8812 ELECTRONICS", "Category": "Shopping & Retail", "Debit": 145.20, "Credit": None, "Balance": 4009.50},
    {"Date": "2024-01-10", "Description": "CHEVRON 0092495 FUEL", "Category": "Transportation & Fuel", "Debit": 48.50, "Credit": None, "Balance": 3961.00},
    {"Date": "2024-01-12", "Description": "EQUINOX FITNESS MONTHLY GYM MEMBERSHIP", "Category": "Healthcare & Medical", "Debit": 49.99, "Credit": None, "Balance": 3911.01},
    {"Date": "2024-01-15", "Description": "NETFLIX.COM MONTHLY SUBSCRIPTION", "Category": "Subscriptions & Media", "Debit": 19.99, "Credit": None, "Balance": 3891.02},
    {"Date": "2024-01-15", "Description": "SPOTIFY USA STREAMING", "Category": "Subscriptions & Media", "Debit": 10.99, "Credit": None, "Balance": 3880.03},
    {"Date": "2024-01-16", "Description": "ACH DEPOSIT: ACME CORP BI-WEEKLY PAYROLL", "Category": "Salary / Income", "Debit": None, "Credit": 3750.00, "Balance": 7630.03},
    {"Date": "2024-01-18", "Description": "CON EDISON ELECTRIC & GAS UTILITY", "Category": "Utilities & Bills", "Debit": 112.40, "Credit": None, "Balance": 7517.63},
    {"Date": "2024-01-20", "Description": "TRADER JOE'S #520 ORGANIC GROCERIES", "Category": "Groceries", "Debit": 84.60, "Credit": None, "Balance": 7433.03},
    {"Date": "2024-01-22", "Description": "DOORDASH - CHIPOTLE MEXICAN GRILL", "Category": "Food & Dining", "Debit": 28.50, "Credit": None, "Balance": 7404.53},
    {"Date": "2024-01-25", "Description": "VERIZON WIRELESS MONTHLY BILL", "Category": "Utilities & Bills", "Debit": 85.00, "Credit": None, "Balance": 7319.53},
    {"Date": "2024-01-28", "Description": "ZELLE FROM ALEX SMITH - TRIP SHARE", "Category": "Transfers & Banking", "Debit": None, "Credit": 120.00, "Balance": 7439.53},
    {"Date": "2024-01-30", "Description": "TARGET STORE #0912 HOME GOODS", "Category": "Shopping & Retail", "Debit": 76.30, "Credit": None, "Balance": 7363.23},

    # --- February 2024 ---
    {"Date": "2024-02-01", "Description": "ACH DEPOSIT: ACME CORP BI-WEEKLY PAYROLL", "Category": "Salary / Income", "Debit": None, "Credit": 3750.00, "Balance": 11113.23},
    {"Date": "2024-02-02", "Description": "ONLINE TRANSFER - RENT TO HIGHLAND APARTMENTS", "Category": "Rent & Housing", "Debit": 1950.00, "Credit": None, "Balance": 9163.23},
    {"Date": "2024-02-04", "Description": "COSTCO WHOLESALE WAREHOUSE #481", "Category": "Groceries", "Debit": 284.10, "Credit": None, "Balance": 8879.13},
    {"Date": "2024-02-07", "Description": "AMAZON.COM*KITCHENWARE & BOOKS", "Category": "Shopping & Retail", "Debit": 92.40, "Credit": None, "Balance": 8786.73},
    {"Date": "2024-02-10", "Description": "SHELL OIL 1092 FUEL", "Category": "Transportation & Fuel", "Debit": 51.00, "Credit": None, "Balance": 8735.73},
    {"Date": "2024-02-12", "Description": "EQUINOX FITNESS MONTHLY GYM MEMBERSHIP", "Category": "Healthcare & Medical", "Debit": 49.99, "Credit": None, "Balance": 8685.74},
    {"Date": "2024-02-15", "Description": "NETFLIX.COM MONTHLY SUBSCRIPTION", "Category": "Subscriptions & Media", "Debit": 19.99, "Credit": None, "Balance": 8665.75},
    {"Date": "2024-02-15", "Description": "SPOTIFY USA STREAMING", "Category": "Subscriptions & Media", "Debit": 10.99, "Credit": None, "Balance": 8654.76},
    {"Date": "2024-02-15", "Description": "ACH DEPOSIT: ACME CORP BI-WEEKLY PAYROLL", "Category": "Salary / Income", "Debit": None, "Credit": 3750.00, "Balance": 12404.76},
    {"Date": "2024-02-18", "Description": "CON EDISON ELECTRIC & GAS UTILITY", "Category": "Utilities & Bills", "Debit": 98.70, "Credit": None, "Balance": 12306.06},
    {"Date": "2024-02-20", "Description": "WHOLE FOODS MARKET #10424 GROCERY", "Category": "Groceries", "Debit": 122.15, "Credit": None, "Balance": 12183.91},
    {"Date": "2024-02-22", "Description": "STARBUCKS STORE #04822 COFFEE", "Category": "Food & Dining", "Debit": 7.15, "Credit": None, "Balance": 12176.76},
    {"Date": "2024-02-25", "Description": "VERIZON WIRELESS MONTHLY BILL", "Category": "Utilities & Bills", "Debit": 85.00, "Credit": None, "Balance": 12091.76},
    {"Date": "2024-02-27", "Description": "UBER TRIP HELP.UBER.COM", "Category": "Transportation & Fuel", "Debit": 24.50, "Credit": None, "Balance": 12067.26},

    # --- March 2024 ---
    {"Date": "2024-03-01", "Description": "ACH DEPOSIT: ACME CORP BI-WEEKLY PAYROLL", "Category": "Salary / Income", "Debit": None, "Credit": 3750.00, "Balance": 15817.26},
    {"Date": "2024-03-02", "Description": "ONLINE TRANSFER - RENT TO HIGHLAND APARTMENTS", "Category": "Rent & Housing", "Debit": 1950.00, "Credit": None, "Balance": 13867.26},
    {"Date": "2024-03-05", "Description": "IRS TREAS 310 TAX REFUND DIRECT DEPOSIT", "Category": "Salary / Income", "Debit": None, "Credit": 1420.00, "Balance": 15287.26},
    {"Date": "2024-03-08", "Description": "APPLE STORE RETAIL - AIRPODS PRO", "Category": "Shopping & Retail", "Debit": 249.00, "Credit": None, "Balance": 15038.26},
    {"Date": "2024-03-11", "Description": "CHEVRON 0092495 FUEL", "Category": "Transportation & Fuel", "Debit": 46.80, "Credit": None, "Balance": 14991.46},
    {"Date": "2024-03-12", "Description": "EQUINOX FITNESS MONTHLY GYM MEMBERSHIP", "Category": "Healthcare & Medical", "Debit": 49.99, "Credit": None, "Balance": 14941.47},
    {"Date": "2024-03-15", "Description": "NETFLIX.COM MONTHLY SUBSCRIPTION", "Category": "Subscriptions & Media", "Debit": 19.99, "Credit": None, "Balance": 14921.48},
    {"Date": "2024-03-15", "Description": "SPOTIFY USA STREAMING", "Category": "Subscriptions & Media", "Debit": 10.99, "Credit": None, "Balance": 14910.49},
    {"Date": "2024-03-15", "Description": "ACH DEPOSIT: ACME CORP BI-WEEKLY PAYROLL", "Category": "Salary / Income", "Debit": None, "Credit": 3750.00, "Balance": 18660.49},
    {"Date": "2024-03-18", "Description": "WHOLE FOODS MARKET #10424 GROCERY", "Category": "Groceries", "Debit": 154.20, "Credit": None, "Balance": 18506.29},
    {"Date": "2024-03-21", "Description": "AMAZON.COM*HOME SUPPLIES", "Category": "Shopping & Retail", "Debit": 68.90, "Credit": None, "Balance": 18437.39},
    {"Date": "2024-03-24", "Description": "CON EDISON ELECTRIC & GAS UTILITY", "Category": "Utilities & Bills", "Debit": 105.30, "Credit": None, "Balance": 18332.09},
    {"Date": "2024-03-25", "Description": "VERIZON WIRELESS MONTHLY BILL", "Category": "Utilities & Bills", "Debit": 85.00, "Credit": None, "Balance": 18247.09},
    {"Date": "2024-03-28", "Description": "FREELANCE DESIGN INVOICE CLIENT PAYMENT", "Category": "Salary / Income", "Debit": None, "Credit": 850.00, "Balance": 19097.09},
    {"Date": "2024-03-30", "Description": "CVS PHARMACY #0312 HEALTH", "Category": "Healthcare & Medical", "Debit": 34.20, "Credit": None, "Balance": 19062.89},

    # --- April 2024 ---
    {"Date": "2024-04-01", "Description": "ACH DEPOSIT: ACME CORP BI-WEEKLY PAYROLL", "Category": "Salary / Income", "Debit": None, "Credit": 3750.00, "Balance": 22812.89},
    {"Date": "2024-04-02", "Description": "ONLINE TRANSFER - RENT TO HIGHLAND APARTMENTS", "Category": "Rent & Housing", "Debit": 1950.00, "Credit": None, "Balance": 20862.89},
    {"Date": "2024-04-05", "Description": "TRADER JOE'S #520 ORGANIC GROCERIES", "Category": "Groceries", "Debit": 94.80, "Credit": None, "Balance": 20768.09},
    {"Date": "2024-04-08", "Description": "AMAZON.COM*SUMMER WEAR", "Category": "Shopping & Retail", "Debit": 115.50, "Credit": None, "Balance": 20652.59},
    {"Date": "2024-04-12", "Description": "EQUINOX FITNESS MONTHLY GYM MEMBERSHIP", "Category": "Healthcare & Medical", "Debit": 49.99, "Credit": None, "Balance": 20602.60},
    {"Date": "2024-04-15", "Description": "NETFLIX.COM MONTHLY SUBSCRIPTION", "Category": "Subscriptions & Media", "Debit": 19.99, "Credit": None, "Balance": 20582.61},
    {"Date": "2024-04-15", "Description": "SPOTIFY USA STREAMING", "Category": "Subscriptions & Media", "Debit": 10.99, "Credit": None, "Balance": 20571.62},
    {"Date": "2024-04-15", "Description": "ACH DEPOSIT: ACME CORP BI-WEEKLY PAYROLL", "Category": "Salary / Income", "Debit": None, "Credit": 3750.00, "Balance": 24321.62},
    {"Date": "2024-04-19", "Description": "CON EDISON ELECTRIC & GAS UTILITY", "Category": "Utilities & Bills", "Debit": 92.10, "Credit": None, "Balance": 24229.52},
    {"Date": "2024-04-22", "Description": "SHELL OIL 1092 FUEL", "Category": "Transportation & Fuel", "Debit": 52.40, "Credit": None, "Balance": 24177.12},
    {"Date": "2024-04-25", "Description": "VERIZON WIRELESS MONTHLY BILL", "Category": "Utilities & Bills", "Debit": 85.00, "Credit": None, "Balance": 24092.12},
    {"Date": "2024-04-29", "Description": "WHOLE FOODS MARKET #10424 GROCERY", "Category": "Groceries", "Debit": 141.60, "Credit": None, "Balance": 23950.52}
]

df = pd.DataFrame(transactions_data)

# Save as CSV
csv_target = os.path.join("sample_data", "comprehensive_bank_statement.csv")
df.to_csv(csv_target, index=False)
print(f"Generated {csv_target} with {len(df)} transactions.")

# Save as Excel
xlsx_target = os.path.join("sample_data", "comprehensive_bank_statement.xlsx")
df.to_excel(xlsx_target, index=False, engine="openpyxl")
print(f"Generated {xlsx_target} with {len(df)} transactions.")
