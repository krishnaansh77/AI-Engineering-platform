"""Q&A query API endpoint using hybrid retrieval and LLM response generation with citations."""
import logging
import hashlib
import json
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from redis import asyncio as redis

from app.api.schemas import CitationSchema, EvaluationRequest, FeedbackRequest, QueryRequest, QueryResponse, SearchResponse, SearchResultSchema
from app.api.errors import error_detail
from app.api.auth import get_current_user, require_repository_access
from app.config import settings
from app.database import get_db
from app.models.repository import Repository
from app.models.query_feedback import QueryFeedback
from app.models.query_event import QueryEvent
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.services.query_cache import build_query_cache_key
from app.services.evaluation_service import aggregate_scores, score_retrieval
from app.services.usage_service import consume_llm_request, estimate_llm_cost

logger = logging.getLogger(__name__)
router = APIRouter(tags=["query"], dependencies=[Depends(get_current_user), Depends(require_repository_access)])


async def _read_cached_query(key: str) -> dict | None:
    client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        cached = await client.get(key)
        return json.loads(cached) if cached else None
    except Exception as exc:
        logger.warning("Query cache read failed: %s", exc)
        return None
    finally:
        await client.aclose()


async def _write_cached_query(key: str, payload: dict) -> None:
    client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await client.setex(key, settings.QUERY_CACHE_TTL_SECONDS, json.dumps(payload))
    except Exception as exc:
        logger.warning("Query cache write failed: %s", exc)
    finally:
        await client.aclose()


@router.post("/repos/{repo_id}/query", response_model=QueryResponse)
async def query_repository(
    repo_id: uuid.UUID,
    payload: QueryRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
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

    cache_key = build_query_cache_key(
        repo.id,
        repo.last_indexed_at.isoformat() if repo.last_indexed_at else None,
        payload.question,
        payload.top_k,
    )
    cached_response = await _read_cached_query(cache_key)
    if cached_response:
        return QueryResponse(**cached_response, cached=True)

    allowed, _remaining = await consume_llm_request(settings.REDIS_URL, user.id, settings.LLM_DAILY_REQUEST_LIMIT)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=error_detail("LLM_DAILY_LIMIT", "Your daily AI request budget is exhausted. Cached answers and code search remain available; retry after the quota window resets.", True))

    query_started = time.perf_counter()
    retrieval_started = time.perf_counter()
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
    retrieval_latency_ms = (time.perf_counter() - retrieval_started) * 1000

    # Generate answer with citations
    llm_started = time.perf_counter()
    try:
        query_answer = await llm_service.answer_query(
            query=payload.question,
            retrieved_chunks=retrieved_chunks,
            repo_name=repo.full_name,
        )
    except Exception as exc:
        logger.exception("LLM provider failed for repository %s", repo_id)
        # Keep repository exploration usable during provider quota windows.
        # The local synthesizer is grounded in the same retrieved chunks and
        # makes no external API call. It is deliberately explicit in the
        # response model so users know when AI generation was unavailable.
        if settings.LLM_FALLBACK_PROVIDER.lower() not in {"mock", "local"}:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=error_detail("LLM_PROVIDER_UNAVAILABLE", "The AI provider is temporarily unavailable or over quota. Please retry later or check the configured provider limits.", True),
            ) from exc
        logger.warning("Using local grounded fallback after LLM provider failure")
        from app.providers.llm.mock_llm import MockLLMProvider

        fallback_answer = await LLMService(provider=MockLLMProvider()).answer_query(
            query=payload.question,
            retrieved_chunks=retrieved_chunks,
            repo_name=repo.full_name,
        )
        query_answer = fallback_answer
    llm_latency_ms = (time.perf_counter() - llm_started) * 1000

    db.add(
        QueryEvent(
            repository_id=repo_id,
            question_hash=hashlib.sha256(payload.question.strip().encode("utf-8")).hexdigest(),
            model=query_answer.model,
            retrieval_count=len(retrieved_chunks),
            citation_count=len(query_answer.citations),
            prompt_tokens=query_answer.prompt_tokens,
            completion_tokens=query_answer.completion_tokens,
            retrieval_latency_ms=round(retrieval_latency_ms, 2),
            llm_latency_ms=round(llm_latency_ms, 2),
            total_latency_ms=round((time.perf_counter() - query_started) * 1000, 2),
        )
    )
    await db.commit()

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

    response = QueryResponse(
        answer=query_answer.answer,
        citations=citations,
        model=query_answer.model,
        retrieval_count=len(retrieved_chunks),
        citation_coverage=query_answer.citation_coverage,
    )
    await _write_cached_query(cache_key, response.model_dump())
    return response


@router.get("/repos/{repo_id}/search", response_model=SearchResponse)
async def search_repository(
    repo_id: uuid.UUID,
    q: str = Query(..., min_length=1, max_length=500),
    top_k: int = Query(8, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Search repository code using hybrid retrieval without an LLM call."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {repo_id} not found")
    if repo.status != "ready":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Repository must finish indexing before it can be searched.")

    chunks = await RetrievalService().retrieve(
        query=q,
        repo_id=repo_id,
        db=db,
        top_k=settings.RETRIEVAL_TOP_K,
        final_k=top_k,
    )
    return SearchResponse(
        query=q,
        results=[
            SearchResultSchema(
                file_path=chunk.file_path,
                symbol_name=chunk.symbol_name,
                chunk_type=chunk.chunk_type,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                snippet=chunk.content[:800],
                score=round(chunk.score, 6),
            )
            for chunk in chunks
        ],
    )


@router.post("/repos/{repo_id}/evaluate")
async def evaluate_repository_retrieval(
    repo_id: uuid.UUID,
    payload: EvaluationRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Evaluate hybrid retrieval against expected file paths without generating answers."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {repo_id} not found")
    if repo.status != "ready":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Repository must finish indexing before evaluation is available.")

    case_results = []
    for case in payload.cases:
        retrieval_started = time.perf_counter()
        chunks = await RetrievalService().retrieve(
            query=case.question,
            repo_id=repo_id,
            db=db,
            top_k=settings.RETRIEVAL_TOP_K,
            final_k=payload.top_k,
        )
        retrieval_latency_ms = round((time.perf_counter() - retrieval_started) * 1000, 2)
        metrics = score_retrieval(case.expected_files, [chunk.file_path for chunk in chunks])
        case_results.append({"question": case.question, "expected_files": case.expected_files, "retrieved_files": [chunk.file_path for chunk in chunks], "retrieval_latency_ms": retrieval_latency_ms, **metrics})
    return {"summary": aggregate_scores(case_results), "cases": case_results}


@router.post("/repos/{repo_id}/feedback", status_code=status.HTTP_201_CREATED)
async def submit_query_feedback(
    repo_id: uuid.UUID,
    payload: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Store a user's helpful/not-helpful signal without storing generated code context."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {repo_id} not found")

    feedback = QueryFeedback(
        repository_id=repo_id,
        question=payload.question,
        rating=payload.rating,
        model=payload.model,
        retrieval_count=payload.retrieval_count,
        citation_count=payload.citation_count,
    )
    db.add(feedback)
    await db.commit()
    return {"id": str(feedback.id), "status": "recorded"}


@router.get("/repos/{repo_id}/feedback/summary")
async def get_feedback_summary(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return aggregate answer feedback for a repository."""
    repo_result = await db.execute(select(Repository).where(Repository.id == repo_id))
    if not repo_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {repo_id} not found")

    result = await db.execute(
        select(
            func.count(QueryFeedback.id),
            func.sum(case((QueryFeedback.rating == "helpful", 1), else_=0)),
            func.sum(case((QueryFeedback.rating == "not_helpful", 1), else_=0)),
            func.avg(QueryFeedback.retrieval_count),
            func.avg(QueryFeedback.citation_count),
            func.sum(case((QueryFeedback.citation_count > 0, 1), else_=0)),
            func.avg(case((QueryFeedback.rating == "helpful", QueryFeedback.citation_count), else_=None)),
            func.avg(case((QueryFeedback.rating == "not_helpful", QueryFeedback.citation_count), else_=None)),
            func.sum(case(((QueryFeedback.rating == "helpful") & (QueryFeedback.citation_count > 0), 1), else_=0)),
            func.sum(case(((QueryFeedback.rating == "not_helpful") & (QueryFeedback.citation_count > 0), 1), else_=0)),
        ).where(QueryFeedback.repository_id == repo_id)
    )
    total, helpful, not_helpful, avg_retrieval, avg_citations, cited_answers, helpful_avg_citations, not_helpful_avg_citations, helpful_cited, not_helpful_cited = result.one()
    total = int(total or 0)
    helpful = int(helpful or 0)
    not_helpful = int(not_helpful or 0)
    helpful_cited = int(helpful_cited or 0)
    not_helpful_cited = int(not_helpful_cited or 0)
    return {
        "total": total,
        "helpful": helpful,
        "not_helpful": not_helpful,
        "helpful_rate": round(helpful / total, 3) if total else 0,
        "average_retrieval_count": round(float(avg_retrieval), 2) if avg_retrieval is not None else 0,
        "average_citation_count": round(float(avg_citations), 2) if avg_citations is not None else 0,
        "citation_coverage_rate": round(int(cited_answers or 0) / total, 3) if total else 0,
        "helpful_average_citation_count": round(float(helpful_avg_citations), 2) if helpful_avg_citations is not None else 0,
        "not_helpful_average_citation_count": round(float(not_helpful_avg_citations), 2) if not_helpful_avg_citations is not None else 0,
        "helpful_citation_coverage_rate": round(helpful_cited / helpful, 3) if helpful else 0,
        "not_helpful_citation_coverage_rate": round(not_helpful_cited / not_helpful, 3) if not_helpful else 0,
    }


@router.get("/repos/{repo_id}/query-metrics")
async def get_query_metrics(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return aggregate latency metrics for successful repository questions."""
    repo_result = await db.execute(select(Repository.id).where(Repository.id == repo_id))
    if repo_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {repo_id} not found")
    result = await db.execute(
        select(
            func.count(QueryEvent.id),
            func.avg(QueryEvent.retrieval_latency_ms),
            func.avg(QueryEvent.llm_latency_ms),
            func.avg(QueryEvent.total_latency_ms),
            func.avg(QueryEvent.retrieval_count),
            func.avg(QueryEvent.citation_count),
            func.sum(QueryEvent.prompt_tokens),
            func.sum(QueryEvent.completion_tokens),
        ).where(QueryEvent.repository_id == repo_id)
    )
    total, retrieval, llm, total_latency, retrieval_count, citation_count, prompt_tokens, completion_tokens = result.one()
    return {
        "total_queries": int(total or 0),
        "average_retrieval_latency_ms": round(float(retrieval), 2) if retrieval is not None else 0,
        "average_llm_latency_ms": round(float(llm), 2) if llm is not None else 0,
        "average_total_latency_ms": round(float(total_latency), 2) if total_latency is not None else 0,
        "average_retrieval_count": round(float(retrieval_count), 2) if retrieval_count is not None else 0,
        "average_citation_count": round(float(citation_count), 2) if citation_count is not None else 0,
        "prompt_tokens": int(prompt_tokens or 0),
        "completion_tokens": int(completion_tokens or 0),
        "total_tokens": int((prompt_tokens or 0) + (completion_tokens or 0)),
        "estimated_cost_usd": estimate_llm_cost(
            int(prompt_tokens or 0),
            int(completion_tokens or 0),
            settings.LLM_INPUT_COST_PER_MILLION_TOKENS,
            settings.LLM_OUTPUT_COST_PER_MILLION_TOKENS,
        ),
    }
