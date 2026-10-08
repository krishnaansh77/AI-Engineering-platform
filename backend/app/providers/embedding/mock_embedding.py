"""Deterministic local pseudo-embedding provider for testing without external API costs."""
import hashlib
import math
from typing import List

from app.config import settings
from app.providers.embedding.base import EmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    """Local, offline embedding generator using feature hashing.

    Produces normalized configured-dimension vectors with zero network calls,
    enabling full testability of the pgvector pipeline without API fees.
    """

    def __init__(self, dimension: int | None = None) -> None:
        self._dimension = dimension or settings.EMBEDDING_DIMENSION

    def get_dimension(self) -> int:
        return self._dimension

    def get_provider_name(self) -> str:
        return "mock/local-feature-hasher"

    def _hash_text_to_vector(self, text: str) -> List[float]:
        """Convert text into a deterministic, unit-normalized float vector."""
        vec = [0.0] * self._dimension
        tokens = text.lower().split()

        if not tokens:
            return vec

        for token in tokens:
            # Hash token to an index in the vector
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dimension
            sign = 1.0 if (h & 1) else -1.0
            vec[idx] += sign

        # Unit normalize vector for cosine distance
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]

        return vec

    async def embed(self, texts: List[str]) -> List[List[float]]:
        return [self._hash_text_to_vector(t) for t in texts]

    async def embed_single(self, text: str) -> List[float]:
        return self._hash_text_to_vector(text)
