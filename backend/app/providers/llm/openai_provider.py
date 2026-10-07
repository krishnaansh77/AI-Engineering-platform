"""OpenAI LLM provider implementation."""
import logging
from typing import List

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.config import settings
from app.providers.llm.base import LLMMessage, LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """LLM provider backed by OpenAI's chat completions API."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_LLM_MODEL
        self._temperature = settings.OPENAI_LLM_TEMPERATURE
        self._max_tokens = settings.OPENAI_LLM_MAX_TOKENS

    def get_provider_name(self) -> str:
        return f"openai/{self._model}"

    async def complete(
        self,
        messages: List[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Call the OpenAI chat completions endpoint."""
        openai_messages: List[ChatCompletionMessageParam] = [
            {"role": m.role, "content": m.content}  # type: ignore[typeddict-item]
            for m in messages
        ]

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=openai_messages,
                temperature=temperature if temperature is not None else self._temperature,
                max_tokens=max_tokens if max_tokens is not None else self._max_tokens,
            )
        except Exception as e:
            logger.error("OpenAI API error: %s", e)
            raise

        choice = response.choices[0]
        usage = response.usage

        logger.info(
            "OpenAI completion: model=%s prompt_tokens=%d completion_tokens=%d",
            self._model,
            usage.prompt_tokens if usage else 0,
            usage.completion_tokens if usage else 0,
        )

        return LLMResponse(
            content=choice.message.content or "",
            model=self._model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
        )
