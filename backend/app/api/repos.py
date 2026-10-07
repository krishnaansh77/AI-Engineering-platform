"""API routes for repository management: connect, list, inspect, reindex, and delete."""
import asyncio
import logging
import uuid
from typing import List
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    ConnectRepoRequest,
    RepoStatsResponse,
    RepositoryResponse,
    SourceFileResponse,
)
from app.database import AsyncSessionLocal, get_db
from app.models.repository import Repository
from app.models.source_file import SourceFile
from app.services.indexing_service import IndexingService
from app.services.graph_service import DependencyGraphService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/repos", tags=["repositories"])


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
