"""GitHub Webhook receiver for push events and automated incremental reindexing."""
import asyncio
import json
import logging
from typing import Set

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal, get_db
from app.models.repository import Repository
from app.services.github_service import GitHubService
from app.services.indexing_service import IndexingService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhooks"])


@router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Handle incoming GitHub webhook events to trigger incremental reindexing."""
    body_bytes = await request.body()
    github_service = GitHubService()

    # Verify signature if secret is configured
    if settings.GITHUB_WEBHOOK_SECRET:
        if not x_hub_signature_256:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing X-Hub-Signature-256 header",
            )
        if not github_service.verify_webhook_signature(
            body_bytes, x_hub_signature_256, settings.GITHUB_WEBHOOK_SECRET
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

    if x_github_event == "ping":
        return {"status": "ok", "message": "Pong! Webhook configured successfully."}

    if x_github_event != "push":
        return {"status": "ignored", "message": f"Event '{x_github_event}' not processed"}

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON payload: {e}",
        )

    repo_info = payload.get("repository", {})
    repo_full_name = repo_info.get("full_name")

    if not repo_full_name:
        return {"status": "ignored", "message": "No repository full_name in payload"}

    stmt = select(Repository).where(Repository.full_name == repo_full_name)
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()

    if not repo:
        return {
            "status": "ignored",
            "message": f"Repository '{repo_full_name}' is not indexed in this platform",
        }

    # Extract all added and modified files across commits
    changed_files: Set[str] = set()
    for commit in payload.get("commits", []):
        changed_files.update(commit.get("added", []))
        changed_files.update(commit.get("modified", []))

    if not changed_files:
        return {"status": "ok", "message": "No file changes to re-index"}

    file_list = list(changed_files)
    logger.info(
        "Webhook detected %d changed files for %s: %s",
        len(file_list),
        repo_full_name,
        file_list[:5],
    )

    dispatched = False
    try:
        from app.workers.tasks import reindex_files_task
        reindex_files_task.delay(str(repo.id), file_list)
        dispatched = True
    except Exception as e:
        logger.warning("Could not dispatch Celery task: %s. Using asyncio fallback.", e)

    if not dispatched:
        async def _run_fallback():
            async with AsyncSessionLocal() as session:
                service = IndexingService()
                await service.reindex_files(repo.id, file_list, session)

        asyncio.create_task(_run_fallback())

    return {
        "status": "ok",
        "message": f"Queued reindexing for {len(file_list)} files in {repo_full_name}",
        "changed_files": file_list,
    }
