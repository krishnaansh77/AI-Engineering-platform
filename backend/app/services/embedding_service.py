"""Embedding service for code chunks and search queries."""
import logging
from typing import List, Optional

from app.providers.embedding.base import EmbeddingProvider
from app.providers.embedding.factory import get_embedding_provider
from app.services.parser_service import ParsedChunk

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service to handle embedding generation for code chunks and natural language queries."""

    def __init__(self, provider: Optional[EmbeddingProvider] = None) -> None:
        self.provider = provider or get_embedding_provider()

    def _format_chunk_for_embedding(self, chunk: ParsedChunk) -> str:
        """Format a code chunk with contextual metadata prefix for higher retrieval accuracy."""
        prefix_parts = [f"language: {chunk.language}"]
        if chunk.chunk_type:
            prefix_parts.append(f"type: {chunk.chunk_type}")
        if chunk.parent_symbol:
            prefix_parts.append(f"class: {chunk.parent_symbol}")
        if chunk.symbol_name:
            prefix_parts.append(f"symbol: {chunk.symbol_name}")
        if chunk.docstring:
            prefix_parts.append(f"docstring: {chunk.docstring.strip()[:200]}")

        header = " | ".join(prefix_parts)
        return f"code context: [{header}]\n{chunk.content}"

    async def embed_chunks(self, chunks: List[ParsedChunk]) -> List[List[float]]:
        """Generate vector embeddings for a list of parsed code chunks."""
        if not chunks:
            return []

        formatted_texts = [self._format_chunk_for_embedding(c) for c in chunks]
        logger.info("Generating embeddings for %d code chunks", len(chunks))
        return await self.provider.embed(formatted_texts)

    async def embed_query(self, query: str) -> List[float]:
        """Generate a vector embedding for a natural language or code query."""
        formatted_query = f"query: {query.strip()}"
        return await self.provider.embed_single(formatted_query)
