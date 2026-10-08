"""Hybrid RAG retrieval service combining vector search and BM25 with Reciprocal Rank Fusion."""
import logging
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.code_chunk import CodeChunk
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


def _metadata_ranked_ids(chunks: List[CodeChunk], query: str, limit: int) -> List[uuid.UUID]:
    """Rank chunks by exact query-token matches in paths and symbols.

    This is intentionally a small third retrieval signal for identifier-heavy
    questions such as "where is secret scanning implemented?". It does not
    replace semantic or BM25 retrieval.
    """
    import re

    stop_words = {"where", "is", "are", "how", "what", "which", "does", "the", "in", "to", "of", "a", "an", "and", "for"}

    def tokens(value: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]+", value.lower().replace("_", " ")))

    query_tokens = tokens(query) - stop_words
    if not query_tokens:
        return []
    scored = []
    for chunk in chunks:
        metadata_tokens = tokens(chunk.file_path) | tokens(chunk.symbol_name or "") | tokens(chunk.chunk_type)
        overlap = len(query_tokens & metadata_tokens)
        if overlap:
            scored.append((overlap, chunk.id))
    scored.sort(key=lambda item: (-item[0], str(item[1])))
    return [chunk_id for _, chunk_id in scored[:limit]]


@dataclass
class RetrievedChunk:
    """A retrieved code chunk with relevance score and location metadata."""

    chunk_id: uuid.UUID
    file_path: str
    symbol_name: Optional[str]
    chunk_type: str
    start_line: int
    end_line: int
    content: str
    language: str
    score: float


class RetrievalService:
    """Hybrid code search engine combining dense vector search and sparse BM25 retrieval."""

    def __init__(self, embedding_service: Optional[EmbeddingService] = None) -> None:
        self.embedding_service = embedding_service or EmbeddingService()

    async def retrieve(
        self,
        query: str,
        repo_id: uuid.UUID,
        db: AsyncSession,
        top_k: int = 20,
        final_k: int = 5,
    ) -> List[RetrievedChunk]:
        """Perform hybrid retrieval over repository code chunks.

        1. Vector search using pgvector cosine distance
        2. Sparse BM25 search over code chunks
        3. Reciprocal Rank Fusion (RRF) to merge and rerank
        4. Return top final_k items
        """
        if not query.strip():
            return []

        # 1. Fetch all chunks for BM25 and candidate selection
        query_stmt = select(CodeChunk).where(CodeChunk.repository_id == repo_id)
        result = await db.execute(query_stmt)
        all_chunks = list(result.scalars().all())

        if not all_chunks:
            logger.info("No code chunks found for repository %s", repo_id)
            return []

        # 2. Vector search via pgvector
        vector_ranked_ids: List[uuid.UUID] = []
        try:
            query_embedding = await self.embedding_service.embed_query(query)

            # Cosine distance: lower is closer. Order by distance ascending.
            vec_stmt = (
                select(CodeChunk.id)
                .where(
                    CodeChunk.repository_id == repo_id,
                    CodeChunk.embedding.isnot(None),
                )
                .order_by(CodeChunk.embedding.cosine_distance(query_embedding))
                .limit(top_k)
            )
            vec_result = await db.execute(vec_stmt)
            vector_ranked_ids = [row[0] for row in vec_result.all()]
        except Exception as e:
            logger.error("Vector search failed, falling back to BM25 only: %s", e)

        # 3. BM25 Search with code-aware tokenization and symbol weighting
        bm25_ranked_ids: List[uuid.UUID] = []
        metadata_ranked_ids = _metadata_ranked_ids(all_chunks, query, top_k)
        try:
            import re

            stop_words = {
                "where", "is", "are", "how", "what", "which", "does", "do",
                "the", "in", "to", "of", "a", "an", "and", "or", "for", "with",
                "implemented", "handle", "handling", "work", "works", "defined",
                "code", "this", "that", "it", "from"
            }

            def _tokenize(text: str) -> List[str]:
                tokens = re.findall(r"[A-Za-z0-9_]+", text.lower())
                expanded = []
                for t in tokens:
                    expanded.append(t)
                    parts = t.split("_")
                    if len(parts) > 1:
                        expanded.extend(p for p in parts if p)
                return expanded

            tokenized_corpus = []
            chunk_lookup: Dict[uuid.UUID, CodeChunk] = {}

            for chunk in all_chunks:
                chunk_lookup[chunk.id] = chunk
                # Weight file_path and symbol_name 3x for higher precision on identifier queries
                sym = (chunk.symbol_name or "") + " "
                fp = chunk.file_path + " "
                corpus_text = f"{fp * 3}{sym * 3}{chunk.content}"
                tokenized_corpus.append(_tokenize(corpus_text))

            bm25 = BM25Okapi(tokenized_corpus)
            raw_query_tokens = _tokenize(query)
            tokenized_query = [t for t in raw_query_tokens if t not in stop_words]
            if not tokenized_query:
                tokenized_query = raw_query_tokens

            scores = bm25.get_scores(tokenized_query)

            # Sort chunk indexes by BM25 score descending
            indexed_scores = sorted(
                enumerate(scores), key=lambda x: x[1], reverse=True
            )
            bm25_ranked_ids = [
                all_chunks[idx].id
                for idx, sc in indexed_scores[:top_k]
                if sc > 0
            ]
        except Exception as e:
            logger.error("BM25 search failed: %s", e)
            chunk_lookup = {c.id: c for c in all_chunks}

        # If chunk_lookup was not populated above
        if "chunk_lookup" not in locals() or not chunk_lookup:
            chunk_lookup = {c.id: c for c in all_chunks}

        # 4. Reciprocal Rank Fusion (RRF)
        # score = sum(1 / (k + rank)) where k=60
        rrf_k = 60
        rrf_scores: Dict[uuid.UUID, float] = {}

        for rank, cid in enumerate(vector_ranked_ids, start=1):
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))

        for rank, cid in enumerate(bm25_ranked_ids, start=1):
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))

        for rank, cid in enumerate(metadata_ranked_ids, start=1):
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))

        # If both failed or empty, fallback to first few chunks
        if not rrf_scores:
            logger.warning("Both vector and BM25 returned empty ranks, returning first chunks")
            sorted_chunk_ids = [c.id for c in all_chunks[:final_k]]
            rrf_scores = {cid: 0.1 for cid in sorted_chunk_ids}
        else:
            sorted_chunk_ids = sorted(
                rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True
            )[:final_k]

        retrieved: List[RetrievedChunk] = []
        for cid in sorted_chunk_ids:
            chunk = chunk_lookup.get(cid)
            if chunk:
                retrieved.append(
                    RetrievedChunk(
                        chunk_id=chunk.id,
                        file_path=chunk.file_path,
                        symbol_name=chunk.symbol_name,
                        chunk_type=chunk.chunk_type,
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        content=chunk.content,
                        language=chunk.language,
                        score=rrf_scores.get(cid, 0.0),
                    )
                )

        logger.info(
            "Hybrid retrieval returned %d chunks for query '%s'",
            len(retrieved),
            query,
        )
        return retrieved
