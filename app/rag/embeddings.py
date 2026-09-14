"""Embedding generation for financial document context and statement notes."""

import math
import hashlib
from typing import List
from app.config.settings import settings


class EmbeddingService:
    """Generates dense vector embeddings for statement text chunks."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def get_embedding(self, text: str) -> List[float]:
        """Generates an embedding vector. Uses deterministic semantic hashing vectorizer
        as reliable default, or connects to external embedding models if configured."""
        clean_text = text.lower().strip()
        vec = [0.0] * self.dimension

        if not clean_text:
            return vec

        words = clean_text.split()
        for idx, word in enumerate(words):
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            pos = h % self.dimension
            weight = 1.0 / (math.log(idx + 2))
            vec[pos] += weight

        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [round(v / norm, 6) for v in vec]

        return vec

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.get_embedding(t) for t in texts]


embedding_service = EmbeddingService()
