"""Financial categorization and recurring transaction detection engine."""

import re
from typing import List, Dict, Any, Optional
from collections import defaultdict
from app.models.transaction import NormalizedTransaction, TransactionType

# Mapping of keywords to categories
CATEGORY_RULES = {
    "Salary / Income": [
        "salary", "payroll", "paycheck", "direct dep", "dividend", "interest income",
        "stipend", "bonus", "freelance", "wage"
    ],
    "Food & Dining": [
        "restaurant", "cafe", "coffee", "starbucks", "mcdonald", "burger", "pizza",
        "chipotle", "subway", "diner", "bakery", "uber eats", "doordash", "grubhub",
        "bistro", "taco", "dunkin"
    ],
    "Groceries": [
        "walmart", "target", "costco", "trader joe", "kroger", "whole foods", "safeway",
        "aldi", "supermarket", "grocery", "market", "heb", "publix"
    ],
    "Shopping & Retail": [
        "amazon", "ebay", "apple store", "best buy", "nike", "clothing", "retail",
        "ikea", "home depot", "lowe", "zara", "marshalls", "tj maxx"
    ],
    "Utilities & Bills": [
        "electric", "water", "gas co", "power", "utility", "comcast", "at&t", "verizon",
        "t-mobile", "sprint", "internet", "broadband", "energy", "trash", "waste"
    ],
    "Subscriptions & Media": [
        "netflix", "spotify", "hulu", "disney", "youtube", "apple music", "prime video",
        "openai", "chatgpt", "github", "patreon", "audible", "hbo", "paramount"
    ],
    "Transportation & Fuel": [
        "uber", "lyft", "shell", "chevron", "exxon", "bp", "gasoline", "fuel", "parking",
        "transit", "metro", "subway", "toll", "airline", "delta", "united", "american air"
    ],
    "Rent & Housing": [
        "rent", "mortgage", "apartment", "property", "hoa", "realty", "lease"
    ],
    "Healthcare & Medical": [
        "pharmacy", "cvs", "walgreens", "hospital", "clinic", "dental", "doctor",
        "medical", "health", "optometry"
    ],
    "Transfers & Banking": [
        "transfer", "wire", "zelle", "venmo", "cash app", "paypal", "atm withdrawal",
        "fee", "overdraft", "ach transfer"
    ]
}


class CategorizerService:
    """Categorizes transactions and identifies recurring patterns."""

    @classmethod
    def categorize(cls, description: str, merchant: str, transaction_type: TransactionType) -> str:
        text = f"{description} {merchant}".lower()

        # Income / Salary check for credits
        if transaction_type == TransactionType.CREDIT:
            for kw in CATEGORY_RULES["Salary / Income"]:
                if kw in text:
                    return "Salary / Income"

        for category, keywords in CATEGORY_RULES.items():
            for kw in keywords:
                if kw in text:
                    return category

        return "Income" if transaction_type == TransactionType.CREDIT else "General Expense"

    @classmethod
    def extract_clean_merchant(cls, description: str) -> str:
        """Extract a clean, human-readable merchant name from messy banking narration."""
        desc = description.strip()
        
        # Remove common noise prefixes
        prefixes = [
            r"^pos purchase (?:terminal \d+ )?",
            r"^ach (?:debit|credit|payment|deposit):?\s*",
            r"^debit card purchase -?\s*",
            r"^check card purchase -?\s*",
            r"^recurring payment to\s*",
            r"^payment to\s*",
            r"^online transfer (?:to|from)\s*",
            r"^direct debit\s*",
            r"^upi/(?:cr|dr)/\d+/",
            r"^atm (?:withdrawal|deposit)\s*"
        ]
        for p in prefixes:
            desc = re.sub(p, "", desc, flags=re.IGNORECASE).strip()

        # Remove trailing transaction codes like *1234, #1234, SEATTLE WA, US, etc.
        desc = re.sub(r"\s+\*\d{3,4}\b", "", desc)
        desc = re.sub(r"\s+#\d{2,}\b", "", desc)
        desc = re.sub(r"\s+[A-Z]{2}\s+US\b", "", desc, flags=re.IGNORECASE)
        desc = re.sub(r"\s+[A-Z]{2}\b(?:\s+\d{5})?$", "", desc)  # State codes like CA, NY 10001
        desc = re.sub(r"\s+[\d]{6,}\b", "", desc)  # Large reference numbers

        # Known merchant mapping
        known_merchants = {
            "amazon": "Amazon",
            "walmart": "Walmart",
            "target": "Target",
            "starbucks": "Starbucks",
            "mcdonald": "McDonald's",
            "uber": "Uber",
            "lyft": "Lyft",
            "netflix": "Netflix",
            "spotify": "Spotify",
            "apple": "Apple",
            "google": "Google",
            "microsoft": "Microsoft",
            "costco": "Costco",
            "trader joe": "Trader Joe's",
            "whole foods": "Whole Foods",
            "cvs": "CVS Pharmacy",
            "walgreens": "Walgreens",
            "chevron": "Chevron",
            "shell": "Shell",
            "chase": "Chase Bank",
            "wells fargo": "Wells Fargo",
            "bank of america": "Bank of America",
            "zelle": "Zelle",
            "venmo": "Venmo",
            "paypal": "PayPal"
        }

        desc_lower = desc.lower()
        for key, clean_name in known_merchants.items():
            if key in desc_lower:
                return clean_name

        # Clean punctuation and capitalize
        desc = re.sub(r"[^\w\s\.\-&]", " ", desc)
        desc = re.sub(r"\s+", " ", desc).strip()
        words = desc.split()
        if len(words) > 4:
            words = words[:4]
        cleaned = " ".join(words).title()

        return cleaned if cleaned else "Unknown Merchant"

    @classmethod
    def detect_recurring_transactions(cls, transactions: List[NormalizedTransaction]) -> List[Dict[str, Any]]:
        """Identifies recurring subscriptions and periodic expenses."""
        grouped: Dict[str, List[NormalizedTransaction]] = defaultdict(list)
        for t in transactions:
            # Group by merchant and amount (recurring bills typically have the same amount)
            key = f"{t.merchant.lower()}::{t.amount:.2f}::{t.transaction_type.value}"
            grouped[key].append(t)

        recurring = []
        for key, txns in grouped.items():
            if len(txns) >= 2:
                # Sort by date
                txns_sorted = sorted(txns, key=lambda x: x.date)
                recurring.append({
                    "merchant": txns_sorted[0].merchant,
                    "category": txns_sorted[0].category,
                    "transaction_type": txns_sorted[0].transaction_type.value,
                    "frequency_count": len(txns_sorted),
                    "recurring_amount": txns_sorted[0].amount,
                    "dates": [t.date.isoformat() for t in txns_sorted],
                    "total_spent": round(sum(t.amount for t in txns_sorted), 2)
                })

        # Sort by total recurring spent
        recurring.sort(key=lambda x: x["total_spent"], reverse=True)
        return recurring
