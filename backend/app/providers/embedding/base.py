"""Embedding provider abstract base class."""
from abc import ABC, abstractmethod
from typing import List


class EmbeddingProvider(ABC):
    """Abstract base class for text/code embedding providers.

    Concrete implementations must implement `embed()`, `embed_single()`,
    `get_dimension()`, and `get_provider_name()`.
    """

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts. Returns one vector per input text."""
        ...

    @abstractmethod
    async def embed_single(self, text: str) -> List[float]:
        """Embed a single text. Returns one vector."""
        ...

    @abstractmethod
    def get_dimension(self) -> int:
        """Return the dimensionality of the embedding vectors produced."""
        ...

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return a human-readable name for this provider."""
        ...
