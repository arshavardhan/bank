"""RAG retrieval tool for searching non-numerical statement text, disclosures, and notes."""

from typing import Dict, Any, Optional
from app.rag.vector_store import vector_store


def search_statement_text(
    query: str,
    statement_id: Optional[str] = None,
    top_k: int = 4
) -> Dict[str, Any]:
    """Retrieve textual context and disclosures from uploaded statement documents."""
    results = vector_store.search(query=query, statement_id=statement_id, top_k=top_k)
    return {
        "query": query,
        "results_count": len(results),
        "retrieved_chunks": results
    }
