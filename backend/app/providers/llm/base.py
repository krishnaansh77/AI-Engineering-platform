"""LLM provider abstract base class and message/response types."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass
class LLMMessage:
    """A single message in a conversation."""
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    Concrete implementations must implement `complete()` and `get_provider_name()`.
    This abstraction lets the application swap LLM backends (OpenAI → Anthropic →
    local Ollama) by changing a single environment variable.
    """

    @abstractmethod
    async def complete(
        self,
        messages: List[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Send a list of messages and return the model's response."""
        ...

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return a human-readable name for this provider."""
        ...
