"""OpenAI embedding provider implementation."""
import logging
from typing import List

from openai import AsyncOpenAI

from app.config import settings
from app.providers.embedding.base import EmbeddingProvider

logger = logging.getLogger(__name__)

# OpenAI recommends batches of ≤ 2048 for text-embedding-3-*
_BATCH_SIZE = 512


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding provider backed by OpenAI's text-embedding API."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_EMBEDDING_MODEL
        self._dimension = settings.EMBEDDING_DIMENSION

    def get_dimension(self) -> int:
        return self._dimension

    def get_provider_name(self) -> str:
        return f"openai/{self._model}"

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts, splitting into chunks to respect API limits."""
        if not texts:
            return []

        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            # Strip empty strings — OpenAI rejects them
            batch = [t if t.strip() else " " for t in batch]

            try:
                response = await self._client.embeddings.create(
                    model=self._model,
                    input=batch,
                )
            except Exception as e:
                logger.error("OpenAI Embeddings API error: %s", e)
                raise

            # Sort by index to maintain input order
            sorted_data = sorted(response.data, key=lambda d: d.index)
            all_embeddings.extend(d.embedding for d in sorted_data)

        logger.debug("Embedded %d texts with %s", len(texts), self._model)
        return all_embeddings

    async def embed_single(self, text: str) -> List[float]:
        """Embed a single text string."""
        results = await self.embed([text])
        return results[0]
