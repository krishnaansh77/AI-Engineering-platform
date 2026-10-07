"""Celery background tasks for asynchronous repository indexing."""
import asyncio
import logging
import uuid
from typing import List

from app.database import AsyncSessionLocal, engine
from app.services.indexing_service import IndexingService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.index_repository")
def index_repository_task(repo_id_str: str) -> None:
    """Run full indexing pipeline in a background Celery worker."""
    logger.info("Starting background indexing task for repository %s", repo_id_str)

    async def _run() -> None:
        try:
            async with AsyncSessionLocal() as session:
                service = IndexingService()
                await service.index_repository(uuid.UUID(repo_id_str), session)
        finally:
            # Celery prefork workers execute each task with asyncio.run(),
            # creating a fresh event loop. Dispose the asyncpg pool before
            # that loop closes so the next task cannot reuse loop-bound
            # connections.
            await engine.dispose()

    asyncio.run(_run())


@celery_app.task(name="tasks.reindex_files")
def reindex_files_task(repo_id_str: str, file_paths: List[str]) -> None:
    """Run incremental reindexing for changed files in a background Celery worker."""
    logger.info(
        "Starting background file reindexing task for repo %s (%d files)",
        repo_id_str,
        len(file_paths),
    )

    async def _run() -> None:
        try:
            async with AsyncSessionLocal() as session:
                service = IndexingService()
                await service.reindex_files(uuid.UUID(repo_id_str), file_paths, session)
        finally:
            await engine.dispose()

    asyncio.run(_run())
