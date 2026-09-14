"""API request and response schemas."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.transaction import NormalizedTransaction, FinancialSummary, TransactionType


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    llm_provider: str
    database: str
    qdrant: str
    langfuse: bool


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    file_type: str
    total_transactions: int
    summary: FinancialSummary
    sample_transactions: List[NormalizedTransaction] = []
    warnings: List[str] = []


class AskRequest(BaseModel):
    question: str = Field(..., description="Natural language question about the statement")
    session_id: Optional[str] = Field(default=None, description="Optional session or file ID to restrict queries to")


class ValidationInfo(BaseModel):
    is_valid: bool = True
    grounded_in_tools: bool = True
    claims_verified: bool = True
    consistency_passed: bool = True
    flags: List[str] = []


class AskResponse(BaseModel):
    question: str
    answer: str
    tools_used: List[str] = []
    calculation_results: Dict[str, Any] = {}
    relevant_transactions: List[NormalizedTransaction] = []
    confidence: float = 1.0
    validation: ValidationInfo = Field(default_factory=ValidationInfo)
    source_info: Dict[str, Any] = Field(default_factory=dict)


class TransactionQueryFilter(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    transaction_type: Optional[TransactionType] = None
    merchant: Optional[str] = None
    category: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class TransactionListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    transactions: List[NormalizedTransaction]
