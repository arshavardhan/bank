"""
AegisAI Integration Script for Financial Statement Analysis Agent.

This script demonstrates how AegisAI provides automated reliability,
trust scoring, and out-of-distribution (OOD) anomaly detection for
bank transactions.
"""

from pathlib import Path
import pandas as pd
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from aegis import AegisModel
from aegis.ood.zscore import ZScoreOODDetector


def run_bank_aegis_audit():
    print("=" * 70)
    print("[BANK] AEGISAI BANK TRANSACTION RELIABILITY & ANOMALY AUDIT")
    print("=" * 70)

    # 1. Reference Historical Data for Account Activity
    # Standard transaction patterns categorized by the bank agent
    history = [
        ("Acme Corp", "CREDIT", 4500.0, 4500.0, 2, "Salary / Income"),
        ("Tech Corp", "CREDIT", 5200.0, 5200.0, 1, "Salary / Income"),
        ("Client Consulting", "CREDIT", 3200.0, 3200.0, 15, "Salary / Income"),
        ("Starbucks", "DEBIT", 6.75, 2410.0, 10, "Food & Dining"),
        ("Starbucks", "DEBIT", 7.25, 2147.0, 25, "Food & Dining"),
        ("Chipotle", "DEBIT", 14.50, 2100.0, 12, "Food & Dining"),
        ("McDonalds", "DEBIT", 11.20, 2050.0, 18, "Food & Dining"),
        ("Whole Foods", "DEBIT", 142.50, 2507.0, 5, "Groceries"),
        ("Whole Foods", "DEBIT", 168.20, 4616.0, 5, "Groceries"),
        ("Trader Joes", "DEBIT", 85.0, 2400.0, 14, "Groceries"),
        ("Target", "DEBIT", 88.40, 2134.0, 30, "Shopping & Retail"),
        ("Amazon", "DEBIT", 89.99, 2417.0, 8, "Shopping & Retail"),
        ("Amazon", "DEBIT", 64.20, 2166.0, 20, "Shopping & Retail"),
        ("Con Edison", "DEBIT", 115.40, 2230.0, 18, "Utilities & Bills"),
        ("Con Edison", "DEBIT", 98.60, 4266.0, 18, "Utilities & Bills"),
        ("Verizon", "DEBIT", 85.0, 2300.0, 16, "Utilities & Bills"),
        ("Netflix", "DEBIT", 19.99, 2345.0, 15, "Subscriptions & Media"),
        ("Spotify", "DEBIT", 10.99, 2155.0, 22, "Subscriptions & Media"),
        ("Apartment Co", "DEBIT", 1850.0, 2650.0, 3, "Rent & Housing"),
        ("Chevron", "DEBIT", 45.0, 2365.0, 12, "Transportation & Fuel"),
        ("Chevron", "DEBIT", 48.50, 4211.0, 26, "Transportation & Fuel"),
    ] * 8

    train_df = pd.DataFrame(
        history,
        columns=["merchant", "transaction_type", "amount", "balance", "day_of_month", "category"],
    )

    X_train = train_df[["merchant", "transaction_type", "amount", "balance", "day_of_month"]]
    y_train = train_df["category"]

    # 2. Build Classification & Preprocessing Pipeline
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), ["amount", "balance", "day_of_month"]),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["merchant", "transaction_type"]),
        ]
    )

    clf = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", LogisticRegression(max_iter=500, random_state=42)),
        ]
    )
    clf.fit(X_train, y_train)

    # 3. Initialize AegisModel with Z-score Out-of-Distribution Detector
    detector = ZScoreOODDetector(threshold=5.0)
    aegis = AegisModel(clf, ood_detector=detector).fit(X_train)

    print(f"Reference Training Data: {len(X_train)} historical transactions")
    print(f"AegisModel Fitted: {aegis.is_fitted}")

    # 4. Audit Incoming Statement Transactions (including normal vs anomalous)
    audit_transactions = [
        {"merchant": "Starbucks", "transaction_type": "DEBIT", "amount": 6.85, "balance": 2400.0, "day_of_month": 11, "note": "Normal coffee"},
        {"merchant": "Whole Foods", "transaction_type": "DEBIT", "amount": 145.0, "balance": 2255.0, "day_of_month": 12, "note": "Normal grocery"},
        {"merchant": "Netflix", "transaction_type": "DEBIT", "amount": 19.99, "balance": 2235.0, "day_of_month": 15, "note": "Recurring subscription"},
        {"merchant": "Acme Corp", "transaction_type": "CREDIT", "amount": 4500.0, "balance": 6735.0, "day_of_month": 1, "note": "Regular salary deposit"},
        {"merchant": "Unknown Offshore Broker", "transaction_type": "DEBIT", "amount": 850000.0, "balance": 120.0, "day_of_month": 16, "note": "SUSPICIOUS / OUTLIER WIRE"},
    ]

    test_df = pd.DataFrame(audit_transactions)
    X_test = test_df[["merchant", "transaction_type", "amount", "balance", "day_of_month"]]

    print("\n" + "=" * 70)
    print("TRANSACTION AUDIT RESULTS")
    print("=" * 70)

    reports = aegis.predict_batch(X_test)

    for idx, (rep, raw) in enumerate(zip(reports, audit_transactions)):
        status_flag = "[ANOMALY DETECTED]" if rep.ood else "[VERIFIED IN-DISTRIBUTION]"
        print(f"\nTx #{idx + 1}: {raw['merchant']} | Amount: ${raw['amount']:,.2f} | Type: {raw['transaction_type']} | Note: {raw['note']}")
        print(f"   Status          : {status_flag}")
        print(f"   Predicted Class : {rep.prediction}")
        print(f"   Confidence      : {rep.confidence:.4f}")
        print(f"   Uncertainty     : {rep.uncertainty:.4f}")
        print(f"   OOD Score       : {rep.ood_score:.4f} (Raw Z-score: {rep.metadata['ood_raw_score']:.2f})")
        print(f"   Trust Score     : {rep.trust_score:.4f}")
        print(f"   Risk Level      : {rep.risk_level.value}")
        print(f"   Recommendation  : {rep.recommendation.value}")

    print("\n" + "=" * 70)
    print("AUDIT COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run_bank_aegis_audit()
