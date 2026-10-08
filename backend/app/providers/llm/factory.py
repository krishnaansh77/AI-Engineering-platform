"""Factory function that returns the configured LLM provider."""
from functools import lru_cache
from app.config import settings
from app.providers.llm.base import LLMProvider


@lru_cache()
def get_llm_provider() -> LLMProvider:
    """Return a singleton LLM provider based on the LLM_PROVIDER env var.

    Currently supported:
      - "openai" → OpenAIProvider (default)
      - "anthropic" → AnthropicProvider (Phase 4)
    """
    provider = settings.LLM_PROVIDER.lower()
    if provider == "openai":
        from app.providers.llm.openai_provider import OpenAIProvider
        return OpenAIProvider()
    elif provider == "gemini":
        from app.providers.llm.gemini_provider import GeminiProvider
        return GeminiProvider()
    elif provider == "ollama":
        from app.providers.llm.ollama_provider import OllamaProvider
        return OllamaProvider()
    elif provider in ("mock", "local"):
        from app.providers.llm.mock_llm import MockLLMProvider
        return MockLLMProvider()
    raise ValueError(
        f"Unknown LLM provider: '{provider}'. Set LLM_PROVIDER=openai, gemini, ollama, or mock in your .env file."
    )
