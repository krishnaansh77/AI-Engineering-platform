"""Local embeddings through an Ollama server's native /api/embed endpoint."""
from typing import List

import httpx

from app.config import settings
from app.providers.embedding.base import EmbeddingProvider


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self._base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self._model = settings.OLLAMA_EMBEDDING_MODEL

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        async with httpx.AsyncClient(base_url=self._base_url, timeout=120.0) as client:
            response = await client.post("/api/embed", json={"model": self._model, "input": texts})
            response.raise_for_status()
        vectors = response.json().get("embeddings")
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise ValueError("Ollama returned an invalid embedding batch.")
        dimension = self.get_dimension()
        if any(not isinstance(vector, list) or len(vector) != dimension for vector in vectors):
            raise ValueError(f"Ollama embedding dimension does not match EMBEDDING_DIMENSION={dimension}.")
        return vectors

    async def embed_single(self, text: str) -> List[float]:
        return (await self.embed([text]))[0]

    def get_dimension(self) -> int:
        return settings.EMBEDDING_DIMENSION

    def get_provider_name(self) -> str:
        return f"ollama/{self._model}"
