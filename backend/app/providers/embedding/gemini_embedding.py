"""Google Gemini embedding provider using the current Google GenAI SDK."""
import asyncio
import logging
from typing import List

from google import genai
from google.genai import types

from app.config import settings
from app.providers.embedding.base import EmbeddingProvider

logger = logging.getLogger(__name__)

_BATCH_SIZE = 100  # Google embedding API limit per batch


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using Google's gemini-embedding-001 model.

    Supports configurable Gemini embedding dimensions. We truncate/pad to
    match the configured EMBEDDING_DIMENSION.
    """

    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        self._model = settings.GEMINI_EMBEDDING_MODEL.removeprefix("models/")
        self._dimension = settings.EMBEDDING_DIMENSION

    def get_dimension(self) -> int:
        return self._dimension

    def get_provider_name(self) -> str:
        return f"google/{self._model}"

    def _embed_batch_sync(self, texts: List[str]) -> List[List[float]]:
        """Call Google embedding API once for a batch of texts.

        Sending the whole batch in one request is important for the Gemini
        free tier, whose request quota is much tighter than its token quota.
        """
        contents = [text if text and text.strip() else " " for text in texts]
        response = self._client.models.embed_content(
            model=self._model,
            contents=contents,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=self._dimension,
            ),
        )
        embeddings = [embedding.values for embedding in response.embeddings]
        if len(embeddings) != len(contents):
            raise ValueError(
                f"Gemini returned {len(embeddings)} embeddings for {len(contents)} inputs"
            )

        results = []
        for vec in embeddings:
            # Pad or truncate to match configured dimension
            if len(vec) < self._dimension:
                vec = vec + [0.0] * (self._dimension - len(vec))
            elif len(vec) > self._dimension:
                vec = vec[: self._dimension]
            results.append(vec)
        return results

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts in batches."""
        if not texts:
            return []

        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            batch_embeddings = await asyncio.get_event_loop().run_in_executor(
                None, self._embed_batch_sync, batch
            )
            all_embeddings.extend(batch_embeddings)

        logger.debug(
            "Embedded %d texts with %s (dim=%d)", len(texts), self._model, self._dimension
        )
        return all_embeddings

    async def embed_single(self, text: str) -> List[float]:
        """Embed a single text string."""
        results = await self.embed([text])
        return results[0]
