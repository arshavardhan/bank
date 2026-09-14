"""SQLAlchemy models for persisting statements and normalized transactions."""

from datetime import datetime, timezone, date
from sqlalchemy import Column, String, Float, Date, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


class DBTransactionType(enum.Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class StatementModel(Base):
    __tablename__ = "statements"

    id = Column(String(64), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(32), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    total_transactions = Column(Float, default=0)
    total_credits = Column(Float, default=0.0)
    total_debits = Column(Float, default=0.0)
    net_flow = Column(Float, default=0.0)
    raw_text = Column(Text, nullable=True)

    transactions = relationship("TransactionModel", back_populates="statement", cascade="all, delete-orphan")


class TransactionModel(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String(64), primary_key=True, index=True)
    statement_id = Column(String(64), ForeignKey("statements.id", ondelete="CASCADE"), index=True, nullable=True)
    date = Column(Date, nullable=False, index=True)
    description = Column(Text, nullable=False)
    merchant = Column(String(255), nullable=False, index=True)
    transaction_type = Column(SQLEnum(DBTransactionType), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    balance = Column(Float, nullable=True)
    category = Column(String(100), default="Uncategorized", index=True)
    source = Column(String(255), nullable=False)

    statement = relationship("StatementModel", back_populates="transactions")
