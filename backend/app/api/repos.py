"""API routes for repository management: connect, list, inspect, reindex, and delete."""
import asyncio
import json
import logging
import uuid
import git
import httpx
from datetime import datetime, timezone
from typing import List, Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from redis import asyncio as redis

from app.api.schemas import (
    ConnectRepoRequest,
    DocumentationPreviewRequest,
    PRComparisonRequest,
    RepoStatsResponse,
    RepositoryResponse,
    SourceFileResponse,
)
from app.database import AsyncSessionLocal, get_db
from app.config import settings
from app.models.repository import Repository
from app.models.source_file import SourceFile
from app.models.query_feedback import QueryFeedback
from app.models.query_event import QueryEvent
from app.services.indexing_service import IndexingService
from app.services.graph_service import DependencyGraphService
from app.services.github_service import GitHubService
from app.services.retrieval_service import RetrievalService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/repos", tags=["repositories"])


async def _read_issue_cache(key: str) -> list | None:
    client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        cached = await client.get(key)
        return json.loads(cached) if cached else None
    except Exception as exc:
        logger.warning("Issue cache read failed: %s", exc)
        return None
    finally:
        await client.aclose()


async def _write_issue_cache(key: str, issues: list) -> None:
    client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await client.setex(key, 300, json.dumps(issues))
    except Exception as exc:
        logger.warning("Issue cache write failed: %s", exc)
    finally:
        await client.aclose()


def _extract_full_name(github_url: str) -> str:
    """Parse 'owner/repo' slug from a github.com URL."""
    parsed = urlparse(github_url.rstrip("/"))
    path_parts = [p for p in parsed.path.split("/") if p]
    if len(path_parts) < 2:
        raise ValueError("Invalid GitHub URL. Must be in the format 'https://github.com/owner/repo'")
    return f"{path_parts[0]}/{path_parts[1]}"


def _dispatch_indexing_task(repo_id: uuid.UUID) -> None:
    """Dispatch indexing job via Celery worker if available, with in-process fallback."""
    repo_id_str = str(repo_id)
    dispatched_celery = False

    try:
        from app.workers.tasks import index_repository_task
        index_repository_task.delay(repo_id_str)
        dispatched_celery = True
        logger.info("Enqueued Celery indexing task for repo %s", repo_id_str)
    except Exception as e:
        logger.warning(
            "Could not dispatch Celery task (%s). Falling back to background asyncio task.",
            e,
        )

    if not dispatched_celery:
        async def _run_in_process():
            async with AsyncSessionLocal() as session:
                service = IndexingService()
                await service.index_repository(repo_id, session)

        asyncio.create_task(_run_in_process())


@router.post("/connect", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def connect_repository(
    payload: ConnectRepoRequest,
    db: AsyncSession = Depends(get_db),
) -> Repository:
    """Connect a new GitHub repository and initiate background indexing."""
    try:
        full_name = _extract_full_name(payload.github_url)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Check if already connected
    stmt = select(Repository).where(Repository.full_name == full_name)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        if existing.status in ("ready", "indexing"):
            return existing
        # If in error or pending, restart indexing
        existing.status = "pending"
        existing.error_message = None
        await db.commit()
        _dispatch_indexing_task(existing.id)
        return existing

    repo_name = payload.name.strip() if payload.name else full_name.split("/")[-1]
    repo = Repository(
        name=repo_name,
        full_name=full_name,
        github_url=payload.github_url.rstrip("/"),
        status="pending",
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)

    _dispatch_indexing_task(repo.id)
    return repo


@router.get("", response_model=List[RepositoryResponse])
async def list_repositories(
    db: AsyncSession = Depends(get_db),
) -> List[Repository]:
    """List all connected repositories ordered by newest first."""
    stmt = select(Repository).order_by(desc(Repository.created_at))
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Repository:
    """Retrieve detailed state and indexing status for a single repository."""
    stmt = select(Repository).where(Repository.id == repo_id)
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        )
    return repo


@router.post("/{repo_id}/reindex", status_code=status.HTTP_202_ACCEPTED)
async def reindex_repository(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger a manual re-index of the repository."""
    stmt = select(Repository).where(Repository.id == repo_id)
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        )

    repo.status = "pending"
    repo.error_message = None
    await db.commit()

    _dispatch_indexing_task(repo.id)
    return {"message": "Reindexing triggered successfully", "repository_id": str(repo_id)}


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a repository and all associated files and chunks (cascading)."""
    stmt = select(Repository).where(Repository.id == repo_id)
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        )
    await db.delete(repo)
    await db.commit()


@router.get("/{repo_id}/stats", response_model=RepoStatsResponse)
async def get_repository_stats(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RepoStatsResponse:
    """Return high-level summary statistics for a repository."""
    stmt = select(Repository).where(Repository.id == repo_id)
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        )
    return RepoStatsResponse(
        file_count=repo.file_count,
        chunk_count=repo.chunk_count,
        languages=repo.languages or [],
        frameworks=repo.frameworks or [],
        last_indexed_at=repo.last_indexed_at,
    )


@router.get("/{repo_id}/files", response_model=List[SourceFileResponse])
async def list_repository_files(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> List[SourceFile]:
    """List all indexed source files for a given repository."""
    stmt = select(SourceFile).where(SourceFile.repository_id == repo_id).order_by(SourceFile.file_path)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{repo_id}/graph/files")
async def get_file_dependency_graph(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return the repository's resolved file-level import dependency graph."""
    repo_result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = repo_result.scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        )
    if repo.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repository must finish indexing before its dependency graph is available.",
        )
    return await DependencyGraphService().build_file_graph(repo_id, db)


@router.get("/{repo_id}/history")
async def get_repository_history(
    repo_id: uuid.UUID,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return recent commit history from the repository's local clone."""
    repo_result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repository = repo_result.scalar_one_or_none()
    if not repository:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {repo_id} not found")
    if repository.status != "ready":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Repository must finish indexing before history is available.")
    if not repository.clone_path:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Repository clone is unavailable.")
    try:
        commits = GitHubService().get_commit_history(repository.clone_path, limit)
    except (git.exc.NoSuchPathError, git.exc.InvalidGitRepositoryError) as exc:
        logger.warning("History unavailable for repository %s: %s", repo_id, exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Repository history is unavailable.")
    graph = await DependencyGraphService().build_file_graph(repo_id, db)
    for commit in commits:
        changed_paths = set(commit["files"]) & {node["id"] for node in graph["nodes"]}
        impacted = DependencyGraphService.expand_dependents(changed_paths, graph["edges"])
        commit["impact_count"] = len(impacted)
    return {"commits": commits, "count": len(commits)}


@router.get("/{repo_id}/source/{file_path:path}")
async def get_repository_source_file(
    repo_id: uuid.UUID,
    file_path: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return a bounded source preview from the repository clone."""
    repo_result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repository = repo_result.scalar_one_or_none()
    if not repository:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {repo_id} not found")
    if repository.status != "ready":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Repository must finish indexing before source is available.")
    if not repository.clone_path:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Repository clone is unavailable.")
    try:
        return GitHubService().read_source_file(repository.clone_path, file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source file not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/{repo_id}/architecture")
async def get_repository_architecture(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return inferred architecture layers and their cross-layer links."""
    repo_result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repository = repo_result.scalar_one_or_none()
    if not repository:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {repo_id} not found")
    if repository.status != "ready":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Repository must finish indexing before architecture is available.")
    return await DependencyGraphService().build_architecture_summary(repo_id, db)


@router.get("/{repo_id}/test-intelligence")
async def get_test_intelligence(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return heuristic relationships between tests and source files."""
    repo_result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repository = repo_result.scalar_one_or_none()
    if not repository:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {repo_id} not found")
    if repository.status != "ready":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Repository must finish indexing before test intelligence is available.")
    return await DependencyGraphService().build_test_summary(repo_id, db)


@router.get("/{repo_id}/tour")
async def get_repository_tour(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return key connected files and symbols for repository onboarding."""
    repo_result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repository = repo_result.scalar_one_or_none()
    if not repository:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {repo_id} not found")
    if repository.status != "ready":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Repository must finish indexing before its tour is available.")
    return await DependencyGraphService().build_repository_tour(repo_id, db)


@router.get("/{repo_id}/documentation")
async def get_repository_documentation(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return safely bounded README and documentation files."""
    repo_result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repository = repo_result.scalar_one_or_none()
    if not repository:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {repo_id} not found")
    if repository.status != "ready":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Repository must finish indexing before documentation is available.")
    if not repository.clone_path:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Repository clone is unavailable.")
    return {"documents": GitHubService().list_documentation_files(repository.clone_path)}


@router.post("/{repo_id}/documentation/generate-preview")
async def generate_documentation_preview(
    repo_id: uuid.UUID,
    payload: DocumentationPreviewRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate a bounded, citation-backed documentation draft without saving it."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repository = result.scalar_one_or_none()
    if not repository:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {repo_id} not found")
    if repository.status != "ready" or not repository.clone_path:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Repository must be ready before documentation can be generated.")
    try:
        source = GitHubService().read_source_file(repository.clone_path, payload.file_path, max_bytes=50_000)
        line_count = source["content"].count("\n") + 1
        content, model, prompt_tokens, completion_tokens = await LLMService().generate_documentation_preview(
            source["file_path"], source["content"], payload.audience
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source file was not found in the repository.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Documentation provider failed for repository %s", repo_id)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Documentation generation is temporarily unavailable or over quota.") from exc
    return {
        "file_path": source["file_path"],
        "audience": payload.audience,
        "preview": content,
        "citation": {"file_path": source["file_path"], "start_line": 1, "end_line": line_count},
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "saved": False,
    }


@router.get("/{repo_id}/pr-analysis/latest")
async def analyze_latest_repository_change(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return PR-style review signals for the latest local commit."""
    repo_result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repository = repo_result.scalar_one_or_none()
    if not repository:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {repo_id} not found")
    if repository.status != "ready":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Repository must finish indexing before change analysis is available.")
    if not repository.clone_path:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Repository clone is unavailable.")
    try:
        return GitHubService().analyze_latest_commit(repository.clone_path)
    except (git.exc.NoSuchPathError, git.exc.InvalidGitRepositoryError, ValueError) as exc:
        logger.warning("Latest change unavailable for repository %s: %s", repo_id, exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Latest change is unavailable.")


@router.get("/{repo_id}/pr-analysis/commit/{commit_sha}")
async def analyze_repository_commit(
    repo_id: uuid.UUID,
    commit_sha: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return PR-style review signals for a selected local commit."""
    repo_result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repository = repo_result.scalar_one_or_none()
    if not repository:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {repo_id} not found")
    if repository.status != "ready" or not repository.clone_path:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Repository must be ready before commit analysis is available.")
    try:
        return GitHubService().analyze_commit(repository.clone_path, commit_sha)
    except (git.exc.NoSuchPathError, git.exc.InvalidGitRepositoryError, git.exc.BadName, ValueError) as exc:
        logger.warning("Commit %s unavailable for repository %s: %s", commit_sha, repo_id, exc)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commit is unavailable in the local clone.") from exc


@router.post("/{repo_id}/pr-analysis/compare")
async def compare_repository_changes(
    repo_id: uuid.UUID,
    payload: PRComparisonRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Compare two local commits and add dependency-impact signals."""
    repo_result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repository = repo_result.scalar_one_or_none()
    if not repository:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {repo_id} not found")
    if repository.status != "ready" or not repository.clone_path:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Repository must be ready before PR comparison is available.")
    try:
        analysis = GitHubService().compare_commits(repository.clone_path, payload.base, payload.head)
        graph = await DependencyGraphService().build_file_graph(repo_id, db)
        changed_paths = set(analysis["source_files"]) & {node["id"] for node in graph["nodes"]}
        analysis["impacted_files"] = sorted(DependencyGraphService.expand_dependents(changed_paths, graph["edges"]))
        if analysis["impacted_files"]:
            analysis["recommendations"].append(f"Review {len(analysis['impacted_files'])} downstream files connected by imports.")
        return analysis
    except (git.exc.NoSuchPathError, git.exc.InvalidGitRepositoryError, git.exc.BadName, git.exc.GitCommandError, ValueError) as exc:
        logger.warning("PR comparison unavailable for repository %s: %s", repo_id, exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Base or head commit is unavailable in the local clone.") from exc


@router.get("/{repo_id}/technical-debt")
async def get_technical_debt_signals(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return measurable structural hotspots for technical-debt review."""
    repo_result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repository = repo_result.scalar_one_or_none()
    if not repository:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {repo_id} not found")
    if repository.status != "ready":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Repository must finish indexing before debt signals are available.")
    return await DependencyGraphService().build_debt_summary(repo_id, db)


@router.get("/{repo_id}/documentation/quality")
async def get_documentation_quality(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return symbol-level documentation coverage and gaps."""
    repo_result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repository = repo_result.scalar_one_or_none()
    if not repository:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {repo_id} not found")
    if repository.status != "ready":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Repository must finish indexing before documentation quality is available.")
    return await DependencyGraphService().build_documentation_quality(repo_id, db)


@router.get("/{repo_id}/issues")
async def list_repository_issues(
    repo_id: uuid.UUID,
    limit: int = 20,
    state: Literal["open", "closed", "all"] = "open",
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List GitHub issues for a connected repository."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repository = result.scalar_one_or_none()
    if not repository:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {repo_id} not found")
    cache_key = f"aise:issues:{repo_id}:{repository.last_indexed_at.isoformat() if repository.last_indexed_at else 'unindexed'}:{state}:{max(1, min(limit, 50))}"
    cached = await _read_issue_cache(cache_key)
    if cached is not None:
        return {"issues": cached, "cached": True, "state": state}
    try:
        issues = await GitHubService().list_issues(repository.github_url, settings.GITHUB_PAT, limit, state)
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Could not fetch issues for repository %s: %s", repo_id, exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="GitHub issues are unavailable or rate-limited. Retry shortly or configure GITHUB_PAT.") from exc
    await _write_issue_cache(cache_key, issues)
    return {"issues": issues, "cached": False, "state": state}


@router.get("/{repo_id}/issues/{issue_number}/analysis")
async def analyze_repository_issue(
    repo_id: uuid.UUID,
    issue_number: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Find indexed code likely related to one open GitHub issue."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repository = result.scalar_one_or_none()
    if not repository:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {repo_id} not found")
    if repository.status != "ready":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Repository must finish indexing before issue analysis is available.")
    try:
        issues = await GitHubService().list_issues(repository.github_url, settings.GITHUB_PAT, 50, "all")
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="GitHub issues are unavailable or rate-limited. Retry shortly or configure GITHUB_PAT.") from exc
    issue = next((item for item in issues if item["number"] == issue_number), None)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    chunks = await RetrievalService().retrieve(
        query=f"{issue['title']}\n{issue['body']}",
        repo_id=repo_id,
        db=db,
        top_k=settings.RETRIEVAL_TOP_K,
        final_k=5,
    )
    return {
        "issue": issue,
        "relevant_files": [
            {
                "file_path": chunk.file_path,
                "symbol_name": chunk.symbol_name,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "score": round(chunk.score, 6),
            }
            for chunk in chunks
        ],
    }


@router.get("/{repo_id}/report.md", response_class=PlainTextResponse)
async def export_repository_report(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    """Export a structural repository intelligence report as Markdown."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repository = result.scalar_one_or_none()
    if not repository:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {repo_id} not found")
    if repository.status != "ready":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Repository must finish indexing before a report is available.")

    graph_service = DependencyGraphService()
    tour = await graph_service.build_repository_tour(repo_id, db)
    architecture = await graph_service.build_architecture_summary(repo_id, db)
    tests = await graph_service.build_test_summary(repo_id, db)
    docs = await graph_service.build_documentation_quality(repo_id, db)
    history = GitHubService().get_commit_history(repository.clone_path, 5) if repository.clone_path else []
    feedback_result = await db.execute(
        select(
            func.count(QueryFeedback.id),
            func.sum(case((QueryFeedback.rating == "helpful", 1), else_=0)),
        ).where(QueryFeedback.repository_id == repo_id)
    )
    feedback_total, feedback_helpful = feedback_result.one()
    metrics_result = await db.execute(
        select(func.count(QueryEvent.id), func.avg(QueryEvent.total_latency_ms)).where(QueryEvent.repository_id == repo_id)
    )
    query_total, average_latency = metrics_result.one()
    feedback_total = int(feedback_total or 0)
    feedback_helpful = int(feedback_helpful or 0)

    lines = [
        f"# Repository Intelligence Report: {repository.full_name}",
        "",
        f"Generated from the indexed repository on {datetime.now(timezone.utc).isoformat()}.",
        "",
        "## Summary",
        f"- Files: {tour['file_count']}",
        f"- Dependency relationships: {tour['relationship_count']}",
        f"- Source symbols: {docs['symbol_count']}",
        f"- Documentation coverage: {round(docs['coverage'] * 100)}%",
        f"- Test-linked source files: {tests['tested_file_count']} / {tests['source_file_count']}",
        f"- Answer helpful rate: {round(feedback_helpful / feedback_total * 100)}% ({feedback_total} ratings)" if feedback_total else "- Answer helpful rate: no ratings yet",
        f"- Successful questions: {int(query_total or 0)}",
        f"- Average question latency: {round(float(average_latency))} ms" if average_latency is not None else "- Average question latency: no queries yet",
        "",
        "## Architecture Layers",
    ]
    lines.extend(f"- **{layer['name']}**: {layer['file_count']} files" for layer in architecture["layers"])
    lines.extend(["", "## Key Files"])
    lines.extend(f"- `{item['file_path']}` — {item['connections']} connections ({item['layer']})" for item in tour["key_files"])
    lines.extend(["", "## Documentation Gaps"])
    lines.extend(f"- `{gap['file_path']}` — {gap['undocumented_symbols']} undocumented symbols" for gap in docs["gaps"][:10])
    lines.extend(["", "## Recent Commits"])
    lines.extend(f"- `{commit['short_sha']}` {commit['message']} ({commit['author']})" for commit in history)
    lines.extend(["", "---", "This report contains structural signals and should be reviewed alongside runtime coverage and human code review."])
    return PlainTextResponse("\n".join(lines), media_type="text/markdown")
