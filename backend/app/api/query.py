"""Q&A query API endpoint using hybrid retrieval and LLM response generation with citations."""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import CitationSchema, QueryRequest, QueryResponse
from app.config import settings
from app.database import get_db
from app.models.repository import Repository
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["query"])


@router.post("/repos/{repo_id}/query", response_model=QueryResponse)
async def query_repository(
    repo_id: uuid.UUID,
    payload: QueryRequest,
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    """Ask a question about the repository codebase and receive an answer with source citations."""
    # Verify repository existence
    stmt = select(Repository).where(Repository.id == repo_id)
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        )

    if repo.status == "indexing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repository is currently indexing. Please wait until indexing completes before querying.",
        )

    if repo.status == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository indexing failed with error: {repo.error_message}",
        )

    retrieval_service = RetrievalService()
    llm_service = LLMService()

    # Retrieve relevant code chunks via hybrid search
    retrieved_chunks = await retrieval_service.retrieve(
        query=payload.question,
        repo_id=repo_id,
        db=db,
        top_k=settings.RETRIEVAL_TOP_K,
        final_k=payload.top_k,
    )

    # Generate answer with citations
    try:
        query_answer = await llm_service.answer_query(
            query=payload.question,
            retrieved_chunks=retrieved_chunks,
            repo_name=repo.full_name,
        )
    except Exception as exc:
        logger.exception("LLM provider failed for repository %s", repo_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The AI provider is temporarily unavailable or over quota. "
                "Please retry later or check the configured provider limits."
            ),
        ) from exc

    citations = [
        CitationSchema(
            file_path=c.file_path,
            symbol_name=c.symbol_name,
            chunk_type=c.chunk_type,
            start_line=c.start_line,
            end_line=c.end_line,
        )
        for c in query_answer.citations
    ]

    return QueryResponse(
        answer=query_answer.answer,
        citations=citations,
        model=query_answer.model,
        retrieval_count=len(retrieved_chunks),
    )
