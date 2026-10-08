"""Google Gemini LLM provider using the current Google GenAI SDK."""
import logging
from typing import List, Optional

from google import genai
from google.genai import types

from app.config import settings
from app.providers.llm.base import LLMMessage, LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """LLM provider backed by Google's Gemini API."""

    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        # The new SDK expects the bare model ID, while older deployments may
        # still have a ``models/`` prefix in their environment variable.
        self._model_name = settings.GEMINI_LLM_MODEL.removeprefix("models/")
        self._temperature = settings.OPENAI_LLM_TEMPERATURE  # Reuse temperature setting
        self._max_tokens = settings.OPENAI_LLM_MAX_TOKENS

    def get_provider_name(self) -> str:
        return f"google/{self._model_name}"

    async def complete(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Send a list of messages to Gemini and return the response."""
        import asyncio

        # Convert our provider-neutral messages to the GenAI content format.
        # Gemini uses "user" and "model" roles (rather than "assistant").
        contents = []
        system_prompt = None

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
                continue
            role = "model" if msg.role == "assistant" else "user"
            text = msg.content
            if system_prompt and not contents:
                text = f"{system_prompt}\n\n{text}"
                system_prompt = None
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=text)]))

        if not contents:
            raise ValueError("No user messages provided")

        config = types.GenerateContentConfig(
            temperature=temperature if temperature is not None else self._temperature,
            max_output_tokens=max_tokens if max_tokens is not None else self._max_tokens,
        )

        def _call_gemini():
            return self._client.models.generate_content(
                model=self._model_name,
                contents=contents,
                config=config,
            )

        try:
            response = await asyncio.get_event_loop().run_in_executor(None, _call_gemini)
        except Exception as e:
            logger.error("Gemini API error: %s", e)
            raise

        content = response.text or ""

        # Extract token usage from metadata if available
        prompt_tokens = 0
        completion_tokens = 0
        try:
            usage = response.usage_metadata
            prompt_tokens = usage.prompt_token_count or 0
            completion_tokens = usage.candidates_token_count or 0
        except Exception:
            pass

        logger.info(
            "Gemini completion: model=%s prompt_tokens=%d completion_tokens=%d",
            self._model_name,
            prompt_tokens,
            completion_tokens,
        )

        return LLMResponse(
            content=content,
            model=self._model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
