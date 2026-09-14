"""Normalization engine mapping varied banking schemas into unified NormalizedTransaction models."""

import re
import hashlib
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from dateutil import parser as date_parser

from app.models.transaction import NormalizedTransaction, TransactionType
from app.services.categorizer import CategorizerService


# Synonyms for column matching
DATE_SYNONYMS = [
    "date", "txndate", "transactiondate", "postingdate", "valuedate", "postdate",
    "transdate", "bookingdate", "tradedate", "clearingdate"
]

DESCRIPTION_SYNONYMS = [
    "description", "narration", "particulars", "details", "memo", "transactiondetails",
    "narrative", "payee", "name", "remarks", "reference", "desc"
]

CREDIT_SYNONYMS = [
    "credit", "deposit", "deposits", "cr", "creditamount", "received", "moneyin", "inflow"
]

DEBIT_SYNONYMS = [
    "debit", "withdrawal", "withdrawals", "dr", "debitamount", "spent", "moneyout", "outflow", "paid"
]

AMOUNT_SYNONYMS = [
    "amount", "netamount", "txnamount", "transactionamount", "transamount"
]

TYPE_SYNONYMS = [
    "type", "transactiontype", "txntype", "transtype", "crdr", "drcr", "flow"
]

BALANCE_SYNONYMS = [
    "balance", "runningbalance", "availablebalance", "closingbalance", "currentbalance", "netbalance"
]


class TransactionNormalizer:
    """Normalizes raw DataFrames from disparate banks into validated NormalizedTransaction models."""

    def normalize(self, df: pd.DataFrame, source: str = "statement") -> Tuple[List[NormalizedTransaction], List[str]]:
        warnings: List[str] = []
        if df.empty:
            return [], ["Uploaded table is empty."]

        # Standardize column headers (lowercase, alphanumeric only for matching)
        col_map = self._map_columns(df.columns)
        has_amount = any(k in col_map for k in ["amount", "credit", "debit"])

        # If key columns not found in top row, scan first 10 rows for embedded table header
        if not col_map.get("date") or not has_amount:
            for r_idx in range(min(len(df), 10)):
                row_vals = [str(v) for v in df.iloc[r_idx].values if pd.notna(v)]
                test_map = self._map_columns(row_vals)
                if test_map.get("date") and any(k in test_map for k in ["amount", "credit", "debit"]):
                    new_cols = [str(c).strip() if pd.notna(c) and str(c).strip() else f"col_{i}" for i, c in enumerate(df.iloc[r_idx])]
                    df = df.iloc[r_idx + 1:].copy()
                    df.columns = new_cols
                    col_map = self._map_columns(df.columns)
                    break

        date_col = col_map.get("date")
        desc_col = col_map.get("desc")
        amount_col = col_map.get("amount")
        credit_col = col_map.get("credit")
        debit_col = col_map.get("debit")
        type_col = col_map.get("type")
        balance_col = col_map.get("balance")

        if not date_col:
            warnings.append("Could not identify a Date column; attempted fallback to first column.")
            date_col = df.columns[0]

        if not desc_col:
            # Pick a text-heavy column
            desc_candidates = [c for c in df.columns if c != date_col and c != balance_col]
            desc_col = desc_candidates[0] if desc_candidates else date_col
            warnings.append(f"Could not explicitly identify Description column; using '{desc_col}'.")

        normalized_txns: List[NormalizedTransaction] = []

        for idx, row in df.iterrows():
            try:
                # 1. Parse Date
                raw_date = row.get(date_col)
                parsed_date = self._parse_date(raw_date)
                if not parsed_date:
                    continue  # Skip header or footer summaries

                # 2. Parse Description & Clean Merchant
                raw_desc = str(row.get(desc_col, "")).strip()
                if not raw_desc or raw_desc.lower() in ["nan", "none", "null"]:
                    raw_desc = "Unlabeled Transaction"

                clean_merchant = CategorizerService.extract_clean_merchant(raw_desc)

                # 3. Parse Amount & Type
                txn_type, parsed_amount = self._determine_amount_and_type(
                    row=row,
                    amount_col=amount_col,
                    credit_col=credit_col,
                    debit_col=debit_col,
                    type_col=type_col
                )

                if parsed_amount is None or parsed_amount <= 0:
                    continue  # Ignore 0.0 or failed amounts

                # 4. Parse Balance
                parsed_balance = None
                if balance_col and pd.notna(row.get(balance_col)):
                    parsed_balance = self._clean_number(row.get(balance_col))

                # 5. Categorize
                category = CategorizerService.categorize(
                    description=raw_desc,
                    merchant=clean_merchant,
                    transaction_type=txn_type
                )

                # 6. Generate Unique ID
                id_seed = f"{source}:{idx}:{parsed_date.isoformat()}:{raw_desc}:{parsed_amount}:{parsed_balance}"
                txn_id = "txn_" + hashlib.sha256(id_seed.encode("utf-8")).hexdigest()[:16]

                txn = NormalizedTransaction(
                    transaction_id=txn_id,
                    date=parsed_date,
                    description=raw_desc,
                    merchant=clean_merchant,
                    transaction_type=txn_type,
                    amount=round(parsed_amount, 2),
                    balance=round(parsed_balance, 2) if parsed_balance is not None else None,
                    category=category,
                    source=source
                )
                normalized_txns.append(txn)

            except Exception as e:
                warnings.append(f"Row {idx} skipped due to normalization error: {e}")

        # Sort chronologically by date
        normalized_txns.sort(key=lambda t: t.date)

        return normalized_txns, warnings

    def _map_columns(self, columns: List[str]) -> Dict[str, str]:
        """Maps table column headers to normalized field keys."""
        mapping: Dict[str, str] = {}
        for col in columns:
            clean = re.sub(r"[^a-zA-Z0-9]", "", str(col).lower())
            
            if "date" not in mapping and any(s == clean or clean.startswith(s) for s in DATE_SYNONYMS):
                mapping["date"] = col
            elif "credit" not in mapping and any(s == clean for s in CREDIT_SYNONYMS):
                mapping["credit"] = col
            elif "debit" not in mapping and any(s == clean for s in DEBIT_SYNONYMS):
                mapping["debit"] = col
            elif "balance" not in mapping and any(s in clean for s in BALANCE_SYNONYMS):
                mapping["balance"] = col
            elif "type" not in mapping and any(s == clean for s in TYPE_SYNONYMS):
                mapping["type"] = col
            elif "amount" not in mapping and any(s == clean for s in AMOUNT_SYNONYMS):
                mapping["amount"] = col
            elif "desc" not in mapping and any(s in clean for s in DESCRIPTION_SYNONYMS):
                mapping["desc"] = col

        return mapping

    def _determine_amount_and_type(
        self,
        row: pd.Series,
        amount_col: Optional[str],
        credit_col: Optional[str],
        debit_col: Optional[str],
        type_col: Optional[str]
    ) -> Tuple[TransactionType, Optional[float]]:
        """Resolves amount and transaction type across split columns and signed amount columns."""
        # Case A: Separate Credit and Debit columns
        if credit_col and debit_col:
            raw_cr = row.get(credit_col)
            raw_dr = row.get(debit_col)
            clean_cr = self._clean_number(raw_cr) if pd.notna(raw_cr) else None
            clean_dr = self._clean_number(raw_dr) if pd.notna(raw_dr) else None

            if clean_cr is not None and clean_cr > 0:
                return TransactionType.CREDIT, clean_cr
            elif clean_dr is not None and clean_dr > 0:
                return TransactionType.DEBIT, clean_dr

        # Case B: Credit column only
        if credit_col and not debit_col:
            raw_cr = row.get(credit_col)
            val = self._clean_number(raw_cr)
            if val and val > 0:
                return TransactionType.CREDIT, val

        # Case C: Debit column only
        if debit_col and not credit_col:
            raw_dr = row.get(debit_col)
            val = self._clean_number(raw_dr)
            if val and val > 0:
                return TransactionType.DEBIT, val

        # Case D: Single Amount column
        if amount_col and pd.notna(row.get(amount_col)):
            raw_amt_str = str(row.get(amount_col)).strip()
            num_val = self._clean_number(raw_amt_str)
            if num_val is None:
                return TransactionType.DEBIT, None

            # Check explicit type column
            if type_col and pd.notna(row.get(type_col)):
                t_val = str(row.get(type_col)).strip().upper()
                if any(cr in t_val for cr in ["CR", "CREDIT", "DEP", "DEPOSIT"]):
                    return TransactionType.CREDIT, abs(num_val)
                elif any(dr in t_val for dr in ["DR", "DEBIT", "WTH", "WITHDRAWAL"]):
                    return TransactionType.DEBIT, abs(num_val)

            # Check for negative signs or parentheses
            is_negative = (
                num_val < 0 or
                raw_amt_str.startswith("-") or
                raw_amt_str.endswith("-") or
                (raw_amt_str.startswith("(") and raw_amt_str.endswith(")"))
            )
            if is_negative:
                return TransactionType.DEBIT, abs(num_val)
            else:
                # Default standard: positive amount without debit indicator is treated as credit if signed column,
                # or debit if it's an expense sheet. Here positive in a single column is credit.
                return TransactionType.CREDIT, abs(num_val)

        return TransactionType.DEBIT, None

    def _clean_number(self, val: Any) -> Optional[float]:
        """Strip currency symbols, commas, trailing minus, and parse float."""
        if val is None or pd.isna(val):
            return None
        s = str(val).strip()
        if not s or s.lower() in ["nan", "none", "-", "--"]:
            return None

        # Handle parentheses (123.45) as negative
        negative = False
        if s.startswith("(") and s.endswith(")"):
            negative = True
            s = s[1:-1].strip()

        if s.endswith("-"):
            negative = True
            s = s[:-1].strip()

        # Remove currency symbols and formatting
        s = re.sub(r"[^\d.-]", "", s)
        try:
            num = float(s)
            return -abs(num) if negative else num
        except ValueError:
            return None

    def _parse_date(self, val: Any) -> Optional[date]:
        """Robust date parsing across varied standard and non-standard banking formats."""
        if val is None or pd.isna(val):
            return None
        s = str(val).strip()
        if not s or s.lower() in ["nan", "none"]:
            return None

        # Clean common timestamp portions if only date is needed
        s = s.split("T")[0]
        s = re.sub(r"\s+\d{2}:\d{2}(?::\d{2})?.*$", "", s)

        # Standard ISO fast-path
        if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
            try:
                return datetime.strptime(s, "%Y-%m-%d").date()
            except ValueError:
                pass

        try:
            # Fallback to dateutil with dayfirst default for international compatibility
            parsed_dt = date_parser.parse(s, fuzzy=False)
            return parsed_dt.date()
        except Exception:
            try:
                # Try dayfirst=True
                parsed_dt = date_parser.parse(s, dayfirst=True, fuzzy=False)
                return parsed_dt.date()
            except Exception:
                return None
