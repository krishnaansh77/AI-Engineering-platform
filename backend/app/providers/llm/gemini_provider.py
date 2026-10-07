"""Google Gemini LLM provider using the google-generativeai SDK."""
import logging
from typing import List, Optional

from app.config import settings
from app.providers.llm.base import LLMMessage, LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """LLM provider backed by Google's Gemini API (gemini-2.5-flash / gemini-2.5-pro)."""

    def __init__(self) -> None:
        import google.generativeai as genai

        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self._model_name = settings.GEMINI_LLM_MODEL
        self._temperature = settings.OPENAI_LLM_TEMPERATURE  # Reuse temperature setting
        self._max_tokens = settings.OPENAI_LLM_MAX_TOKENS
        self._genai = genai

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

        model = self._genai.GenerativeModel(
            model_name=self._model_name,
            generation_config=self._genai.GenerationConfig(
                temperature=temperature if temperature is not None else self._temperature,
                max_output_tokens=max_tokens if max_tokens is not None else self._max_tokens,
            ),
        )

        # Convert messages to Gemini chat format
        # Gemini uses "user" and "model" roles
        system_prompt = None
        chat_history = []

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            elif msg.role == "user":
                if system_prompt and not chat_history:
                    # Prepend system prompt to first user message
                    chat_history.append({
                        "role": "user",
                        "parts": [f"{system_prompt}\n\n{msg.content}"],
                    })
                    system_prompt = None
                else:
                    chat_history.append({"role": "user", "parts": [msg.content]})
            elif msg.role == "assistant":
                chat_history.append({"role": "model", "parts": [msg.content]})

        if not chat_history:
            raise ValueError("No user messages provided")

        # Run synchronous Gemini API call in thread pool to keep async behavior
        last_message = chat_history[-1]["parts"][0]
        history = chat_history[:-1]

        def _call_gemini():
            chat = model.start_chat(history=history)
            return chat.send_message(last_message)

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
