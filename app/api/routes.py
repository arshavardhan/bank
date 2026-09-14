"""FastAPI API routes for bank statement upload, natural language Q&A, and transaction analytics."""

from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.session import get_db
from app.models.schemas import (
    HealthResponse,
    UploadResponse,
    AskRequest,
    AskResponse,
    TransactionQueryFilter,
    TransactionListResponse
)
from app.models.transaction import FinancialSummary, TransactionType
from app.services.statement_service import statement_service
from app.analytics.engine import FinancialAnalyticsEngine
from app.agents.orchestrator import orchestrator

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Service health and subsystem status")
def health_check():
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        llm_provider=settings.LLM_PROVIDER,
        database=settings.DATABASE_URL.split(":///")[0],
        qdrant="connected",
        langfuse=settings.LANGFUSE_ENABLED
    )


@router.post("/upload", response_model=UploadResponse, summary="Upload bank statement (CSV, Excel, PDF, Image)")
async def upload_statement(
    file: UploadFile = File(..., description="Bank statement file"),
    db: Session = Depends(get_db)
):
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        response = statement_service.process_file_upload(
            content=content,
            filename=file.filename or "statement.csv",
            db=db
        )
        return response
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process statement: {str(e)}")


@router.post("/ask", response_model=AskResponse, summary="Ask natural language question about financial statements")
def ask_question(
    request: AskRequest,
    db: Session = Depends(get_db)
):
    transactions = statement_service.get_all_transactions_for_statement(request.session_id)
    if not transactions:
        raise HTTPException(
            status_code=404,
            detail="No financial transactions found. Please upload a bank statement first via POST /upload."
        )

    try:
        response = orchestrator.ask(
            question=request.question,
            transactions=transactions,
            session_id=request.session_id
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing agent orchestrator: {str(e)}")


@router.get("/transactions", response_model=TransactionListResponse, summary="List and filter normalized transactions")
def get_transactions(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    transaction_type: Optional[TransactionType] = Query(None, description="CREDIT or DEBIT"),
    merchant: Optional[str] = Query(None, description="Filter by merchant name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_amount: Optional[float] = Query(None, ge=0),
    max_amount: Optional[float] = Query(None, ge=0),
    statement_id: Optional[str] = Query(None, description="Statement or file ID"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    filters = TransactionQueryFilter(
        start_date=start_date,
        end_date=end_date,
        transaction_type=transaction_type,
        merchant=merchant,
        category=category,
        min_amount=min_amount,
        max_amount=max_amount,
        limit=limit,
        offset=offset
    )

    items, total = statement_service.get_transactions(
        statement_id=statement_id,
        filters=filters,
        db=db
    )

    return TransactionListResponse(
        total=total,
        limit=limit,
        offset=offset,
        transactions=items
    )


@router.get("/summary", response_model=FinancialSummary, summary="Get high-level deterministic financial summary")
def get_summary(
    statement_id: Optional[str] = Query(None, description="Optional statement ID to filter by")
):
    transactions = statement_service.get_all_transactions_for_statement(statement_id)
    if not transactions:
        return FinancialSummary()

    engine = FinancialAnalyticsEngine(transactions)
    return engine.compute_summary()


@router.get("/api/analytics/cost", summary="Get real-time cost, token usage, and observability analytics")
def get_cost_analytics():
    from app.observability.tracer import cost_store
    return cost_store.get_summary()
