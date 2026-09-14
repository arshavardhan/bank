"""SQL-based deterministic analytics executing against the database."""

from typing import Dict, Any, List, Optional
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from app.database.models import TransactionModel, DBTransactionType


class SqlAnalyticsEngine:
    """Executes deterministic SQL aggregate queries over persisted transactions."""

    def __init__(self, db: Session, statement_id: Optional[str] = None):
        self.db = db
        self.statement_id = statement_id

    def _base_query(self):
        q = self.db.query(TransactionModel)
        if self.statement_id:
            q = q.filter(TransactionModel.statement_id == self.statement_id)
        return q

    def get_totals_sql(self) -> Dict[str, Any]:
        q = self._base_query()
        credits_res = q.filter(TransactionModel.transaction_type == DBTransactionType.CREDIT).with_entities(
            func.coalesce(func.sum(TransactionModel.amount), 0.0),
            func.count(TransactionModel.transaction_id)
        ).first()

        debits_res = q.filter(TransactionModel.transaction_type == DBTransactionType.DEBIT).with_entities(
            func.coalesce(func.sum(TransactionModel.amount), 0.0),
            func.count(TransactionModel.transaction_id)
        ).first()

        total_cr = round(float(credits_res[0]), 2)
        count_cr = int(credits_res[1])
        total_dr = round(float(debits_res[0]), 2)
        count_dr = int(debits_res[1])

        return {
            "total_credits": total_cr,
            "credit_count": count_cr,
            "total_debits": total_dr,
            "debit_count": count_dr,
            "net_flow": round(total_cr - total_dr, 2),
            "total_transactions": count_cr + count_dr
        }

    def get_top_merchants_sql(self, limit: int = 10) -> List[Dict[str, Any]]:
        res = (
            self._base_query()
            .filter(TransactionModel.transaction_type == DBTransactionType.DEBIT)
            .with_entities(
                TransactionModel.merchant,
                func.sum(TransactionModel.amount).label("total_spent"),
                func.count(TransactionModel.transaction_id).label("count")
            )
            .group_by(TransactionModel.merchant)
            .order_by(desc("total_spent"))
            .limit(limit)
            .all()
        )
        return [{"merchant": r[0], "total_spent": round(float(r[1]), 2), "count": int(r[2])} for r in res]
