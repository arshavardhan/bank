"""Qdrant vector store integration for textual bank statement notes, terms, and context."""

import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config.settings import settings
from app.rag.embeddings import embedding_service


class StatementVectorStore:
    """Manages statement text chunks, disclosures, and policies in Qdrant."""

    def __init__(self):
        # Supports ':memory:' for zero-setup local dev/tests, or remote host
        if settings.QDRANT_LOCATION == ":memory:":
            self.client = QdrantClient(location=":memory:")
        else:
            self.client = QdrantClient(url=settings.QDRANT_LOCATION)

        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self.dimension = embedding_service.dimension
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            collections = self.client.get_collections().collections
            existing = [c.name for c in collections]
            if self.collection_name not in existing:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=self.dimension,
                        distance=qmodels.Distance.COSINE
                    )
                )
        except Exception as e:
            # Fallback for memory client re-init
            pass

    def index_document(self, statement_id: str, raw_text: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Splits raw statement text into chunks, generates embeddings, and indexes them."""
        if not raw_text or not raw_text.strip():
            return 0

        chunks = self._chunk_text(raw_text)
        if not chunks:
            return 0

        points = []
        for idx, chunk in enumerate(chunks):
            vector = embedding_service.get_embedding(chunk)
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{statement_id}_{idx}"))
            payload = {
                "statement_id": statement_id,
                "chunk_index": idx,
                "text": chunk,
                **(metadata or {})
            }
            points.append(qmodels.PointStruct(id=point_id, vector=vector, payload=payload))

        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        return len(chunks)

    def search(self, query: str, statement_id: Optional[str] = None, top_k: int = 4) -> List[Dict[str, Any]]:
        """Searches statement text chunks for relevant textual context."""
        query_vector = embedding_service.get_embedding(query)

        query_filter = None
        if statement_id:
            query_filter = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="statement_id",
                        match=qmodels.MatchValue(value=statement_id)
                    )
                ]
            )

        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=top_k
            )
            return [
                {
                    "text": hit.payload.get("text", ""),
                    "statement_id": hit.payload.get("statement_id", ""),
                    "score": round(float(hit.score), 4)
                }
                for hit in results
            ]
        except Exception:
            return []

    def _chunk_text(self, text: str, max_words: int = 150) -> List[str]:
        """Splits text into coherent paragraph-level chunks."""
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = []
        current_word_count = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            words = para.split()
            if current_word_count + len(words) > max_words and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = [para]
                current_word_count = len(words)
            else:
                current_chunk.append(para)
                current_word_count += len(words)

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks


vector_store = StatementVectorStore()
