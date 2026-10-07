"""Factory function that returns the configured embedding provider."""
from functools import lru_cache
from app.config import settings
from app.providers.embedding.base import EmbeddingProvider


@lru_cache()
def get_embedding_provider() -> EmbeddingProvider:
    """Return a singleton embedding provider based on EMBEDDING_PROVIDER env var.

    Currently supported:
      - "openai" → OpenAIEmbeddingProvider (default)
      - "local"  → LocalEmbeddingProvider (Phase 4, via Ollama)
    """
    provider = settings.EMBEDDING_PROVIDER.lower()
    if provider == "openai":
        from app.providers.embedding.openai_embedding import OpenAIEmbeddingProvider
        return OpenAIEmbeddingProvider()
    elif provider == "gemini":
        from app.providers.embedding.gemini_embedding import GeminiEmbeddingProvider
        return GeminiEmbeddingProvider()
    elif provider in ("mock", "local"):
        from app.providers.embedding.mock_embedding import MockEmbeddingProvider
        return MockEmbeddingProvider()
    raise ValueError(
        f"Unknown embedding provider: '{provider}'. Set EMBEDDING_PROVIDER=openai, gemini, or mock in .env."
    )
