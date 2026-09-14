"""LangGraph state schema for financial statement orchestrator."""

from typing import TypedDict, List, Dict, Any, Optional
from app.models.transaction import NormalizedTransaction
from app.models.schemas import ValidationInfo


class AgentState(TypedDict):
    """The graph state flowing through each node in the LangGraph workflow."""
    question: str
    session_id: Optional[str]
    transactions: List[NormalizedTransaction]
    intent: str
    selected_tools: List[str]
    tool_params: Dict[str, Dict[str, Any]]
    tool_results: Dict[str, Any]
    relevant_transactions: List[NormalizedTransaction]
    rag_context: Optional[str]
    validation: ValidationInfo
    final_answer: str
    confidence: float
    error: Optional[str]
