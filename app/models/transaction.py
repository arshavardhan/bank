"""Normalized transaction models and financial summary types."""

import datetime as dt
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict


class TransactionType(str, Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class NormalizedTransaction(BaseModel):
    """Core unified schema for all extracted bank statement transactions."""
    transaction_id: str = Field(..., description="Unique identifier for the transaction")
    date: dt.date = Field(..., description="Transaction posting/effective date in YYYY-MM-DD")
    description: str = Field(..., description="Raw or cleaned transaction narrative/description")
    merchant: str = Field(default="Unknown", description="Identified or cleaned merchant/entity name")
    transaction_type: TransactionType = Field(..., description="Transaction type: CREDIT or DEBIT")
    amount: float = Field(..., gt=0, description="Absolute transaction amount (strictly positive)")
    balance: Optional[float] = Field(default=None, description="Account balance following the transaction")
    category: str = Field(default="Uncategorized", description="Expense or income category")
    source: str = Field(default="statement", description="Source document or statement reference")

    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )

    @field_validator("amount")
    @classmethod
    def validate_amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"Amount must be strictly positive, got {v}")
        return round(float(v), 2)

    @field_validator("balance")
    @classmethod
    def round_balance(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            return round(float(v), 2)
        return None

    def signed_amount(self) -> float:
        """Returns signed amount (+ for credit, - for debit)."""
        return self.amount if self.transaction_type == TransactionType.CREDIT else -self.amount


class FinancialSummary(BaseModel):
    """High-level deterministic summary of a transaction dataset."""
    total_credits: float = 0.0
    total_debits: float = 0.0
    net_cash_flow: float = 0.0
    credit_count: int = 0
    debit_count: int = 0
    transaction_count: int = 0
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    start_balance: Optional[float] = None
    end_balance: Optional[float] = None
    average_credit: float = 0.0
    average_debit: float = 0.0
    highest_credit: Optional[NormalizedTransaction] = None
    highest_debit: Optional[NormalizedTransaction] = None
