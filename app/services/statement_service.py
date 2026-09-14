"""Service layer coordinating extraction, normalization, persistence, and querying."""

import os
import uuid
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.transaction import NormalizedTransaction, TransactionType, FinancialSummary
from app.models.schemas import UploadResponse, TransactionQueryFilter
from app.database.models import StatementModel, TransactionModel, DBTransactionType
from app.extraction.csv_excel_extractor import CsvExcelExtractor
from app.extraction.pdf_extractor import PdfExtractor
from app.extraction.ocr_extractor import OcrExtractor
from app.extraction.normalizer import TransactionNormalizer
from app.analytics.engine import FinancialAnalyticsEngine
from app.rag.vector_store import vector_store


class StatementService:
    """Orchestrates file processing pipeline: extract -> normalize -> persist -> index."""

    def __init__(self):
        self.csv_extractor = CsvExcelExtractor()
        self.pdf_extractor = PdfExtractor()
        self.ocr_extractor = OcrExtractor()
        self.normalizer = TransactionNormalizer()
        # In-memory store fallback for active session/testing
        self._memory_statements: Dict[str, List[NormalizedTransaction]] = {}
        self._all_memory_transactions: List[NormalizedTransaction] = []

    def process_file_upload(
        self,
        content: bytes,
        filename: str,
        db: Optional[Session] = None
    ) -> UploadResponse:
        # Validate file size
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise ValueError(f"File size {len(content) / 1024 / 1024:.1f}MB exceeds limit of {settings.MAX_UPLOAD_SIZE_MB}MB")

        # Determine file extension
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise ValueError(f"File extension '{ext}' is not supported. Supported: {settings.ALLOWED_EXTENSIONS}")

        statement_id = f"stmt_{uuid.uuid4().hex[:12]}"
        all_warnings: List[str] = []

        # 1. Extraction
        if ext in ["csv", "xlsx", "xls"]:
            extracted = self.csv_extractor.extract(content, filename)
        elif ext == "pdf":
            extracted = self.pdf_extractor.extract(content, filename)
            # If no tables found, try OCR
            if not extracted.dataframes:
                ocr_data = self.ocr_extractor.extract(content, filename)
                if ocr_data.dataframes:
                    extracted.dataframes.extend(ocr_data.dataframes)
                extracted.raw_text += "\n" + ocr_data.raw_text
                all_warnings.extend(ocr_data.warnings)
        else:
            # Images: png, jpg, jpeg
            extracted = self.ocr_extractor.extract(content, filename)

        all_warnings.extend(extracted.warnings)

        # 2. Normalization
        normalized_txns: List[NormalizedTransaction] = []
        for df in extracted.dataframes:
            txns, norm_warnings = self.normalizer.normalize(df, source=filename)
            normalized_txns.extend(txns)
            all_warnings.extend(norm_warnings)

        # Deduplicate transactions if any overlapping tables
        seen_ids = set()
        deduped: List[NormalizedTransaction] = []
        for t in normalized_txns:
            if t.transaction_id not in seen_ids:
                seen_ids.add(t.transaction_id)
                deduped.append(t)
        normalized_txns = deduped

        # 3. Compute Deterministic Summary
        engine = FinancialAnalyticsEngine(normalized_txns)
        summary = engine.compute_summary()

        # 4. In-Memory Caching
        self._memory_statements[statement_id] = normalized_txns
        self._all_memory_transactions.extend(normalized_txns)

        # 5. Database Persistence
        if db is not None:
            try:
                stmt_record = StatementModel(
                    id=statement_id,
                    filename=filename,
                    file_type=ext,
                    total_transactions=len(normalized_txns),
                    total_credits=summary.total_credits,
                    total_debits=summary.total_debits,
                    net_flow=summary.net_cash_flow,
                    raw_text=extracted.raw_text[:50000] if extracted.raw_text else None
                )
                db.add(stmt_record)

                for t in normalized_txns:
                    txn_record = TransactionModel(
                        transaction_id=t.transaction_id,
                        statement_id=statement_id,
                        date=t.date,
                        description=t.description,
                        merchant=t.merchant,
                        transaction_type=DBTransactionType.CREDIT if t.transaction_type == TransactionType.CREDIT else DBTransactionType.DEBIT,
                        amount=t.amount,
                        balance=t.balance,
                        category=t.category,
                        source=t.source
                    )
                    db.merge(txn_record)
                db.commit()
            except Exception as e:
                db.rollback()
                all_warnings.append(f"DB persistence note: {e}")

        # 6. RAG Vector Store Indexing
        if extracted.raw_text:
            vector_store.index_document(
                statement_id=statement_id,
                raw_text=extracted.raw_text,
                metadata={"filename": filename}
            )

        return UploadResponse(
            file_id=statement_id,
            filename=filename,
            file_type=ext,
            total_transactions=len(normalized_txns),
            summary=summary,
            sample_transactions=normalized_txns[:5],
            warnings=all_warnings
        )

    def get_transactions(
        self,
        statement_id: Optional[str] = None,
        filters: Optional[TransactionQueryFilter] = None,
        db: Optional[Session] = None
    ) -> Tuple[List[NormalizedTransaction], int]:
        """Retrieves transactions with filtering and pagination."""
        txns = self._memory_statements.get(statement_id, self._all_memory_transactions) if statement_id else self._all_memory_transactions

        # If DB available and has records, prefer DB for persistent queries
        if db is not None:
            try:
                q = db.query(TransactionModel)
                if statement_id:
                    q = q.filter(TransactionModel.statement_id == statement_id)
                if filters:
                    if filters.transaction_type:
                        tt = DBTransactionType.CREDIT if filters.transaction_type == TransactionType.CREDIT else DBTransactionType.DEBIT
                        q = q.filter(TransactionModel.transaction_type == tt)
                    if filters.merchant:
                        q = q.filter(TransactionModel.merchant.ilike(f"%{filters.merchant}%"))
                    if filters.category:
                        q = q.filter(TransactionModel.category.ilike(f"%{filters.category}%"))
                    if filters.min_amount:
                        q = q.filter(TransactionModel.amount >= filters.min_amount)
                    if filters.max_amount:
                        q = q.filter(TransactionModel.amount <= filters.max_amount)
                
                total_count = q.count()
                if filters:
                    q = q.offset(filters.offset).limit(filters.limit)
                records = q.all()

                if total_count > 0:
                    converted = [
                        NormalizedTransaction(
                            transaction_id=r.transaction_id,
                            date=r.date,
                            description=r.description,
                            merchant=r.merchant,
                            transaction_type=TransactionType.CREDIT if r.transaction_type == DBTransactionType.CREDIT else TransactionType.DEBIT,
                            amount=r.amount,
                            balance=r.balance,
                            category=r.category,
                            source=r.source
                        )
                        for r in records
                    ]
                    return converted, total_count
            except Exception:
                pass

        # Fallback to in-memory list
        res = list(txns)
        if filters:
            if filters.transaction_type:
                res = [t for t in res if t.transaction_type == filters.transaction_type]
            if filters.merchant:
                m_lower = filters.merchant.lower()
                res = [t for t in res if m_lower in t.merchant.lower()]
            if filters.category:
                c_lower = filters.category.lower()
                res = [t for t in res if c_lower in t.category.lower()]
            if filters.min_amount:
                res = [t for t in res if t.amount >= filters.min_amount]
            if filters.max_amount:
                res = [t for t in res if t.amount <= filters.max_amount]

        total_count = len(res)
        offset = filters.offset if filters else 0
        limit = filters.limit if filters else 50
        return res[offset : offset + limit], total_count

    def get_all_transactions_for_statement(self, statement_id: Optional[str] = None) -> List[NormalizedTransaction]:
        if statement_id and statement_id in self._memory_statements:
            return self._memory_statements[statement_id]
        return self._all_memory_transactions


statement_service = StatementService()
