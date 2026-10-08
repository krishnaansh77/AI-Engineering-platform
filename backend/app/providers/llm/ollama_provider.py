"""Optional local Ollama-compatible chat provider."""
from typing import List

import httpx

from app.config import settings
from app.providers.llm.base import LLMMessage, LLMProvider, LLMResponse


class OllamaProvider(LLMProvider):
    """Call a local Ollama server without sending code to a hosted provider."""

    def __init__(self) -> None:
        self._base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self._model = settings.OLLAMA_LLM_MODEL

    def get_provider_name(self) -> str:
        return f"ollama/{self._model}"

    async def complete(
        self,
        messages: List[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        payload = {
            "model": self._model,
            "messages": [{"role": item.role, "content": item.content} for item in messages],
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else settings.OPENAI_LLM_TEMPERATURE,
                "num_predict": max_tokens if max_tokens is not None else settings.OPENAI_LLM_MAX_TOKENS,
            },
        }
        async with httpx.AsyncClient(base_url=self._base_url, timeout=120.0) as client:
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
        data = response.json()
        return LLMResponse(
            content=str(data.get("message", {}).get("content", "")),
            model=self._model,
            prompt_tokens=int(data.get("prompt_eval_count") or 0),
            completion_tokens=int(data.get("eval_count") or 0),
        )
