"""Repository indexing pipeline orchestrator."""
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.code_chunk import CodeChunk
from app.models.repository import Repository
from app.models.repository_version import RepositoryVersion
from app.models.source_file import SourceFile
from app.services.embedding_service import EmbeddingService
from app.services.github_service import GitHubService
from app.services.github_app_service import GitHubAppService
from app.services.parser_service import ParserService

logger = logging.getLogger(__name__)


def _is_embedding_quota_error(error: Exception) -> bool:
    """Identify provider quota failures without depending on SDK exception types."""
    message = str(error).lower()
    return any(marker in message for marker in ("resource_exhausted", "quota", "rate limit", "429"))


def _chunk_identity(chunk) -> tuple:
    """Stable parser identity used to safely reuse an unchanged file's vectors."""
    return (
        chunk.chunk_type,
        chunk.symbol_name,
        chunk.parent_symbol,
        chunk.start_line,
        chunk.end_line,
        chunk.content,
    )


class IndexingService:
    """Orchestrates cloning, parsing, chunking, embedding, and storage for repositories."""

    def __init__(
        self,
        github_service: Optional[GitHubService] = None,
        parser_service: Optional[ParserService] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ) -> None:
        self.github_service = github_service or GitHubService()
        self.parser_service = parser_service or ParserService()
        self.embedding_service = embedding_service or EmbeddingService()

    async def _reuse_cross_version_embeddings(
        self,
        repo_id: uuid.UUID,
        version_ref: str,
        file_path: str,
        content_hash: str,
        parsed_chunks: list,
        db: AsyncSession,
    ) -> Optional[List[List[float]]]:
        """Reuse vectors for byte-identical files indexed under another ref."""
        source_file = await db.scalar(
            select(SourceFile)
            .where(
                SourceFile.repository_id == repo_id,
                SourceFile.version_ref != version_ref,
                SourceFile.file_path == file_path,
                SourceFile.content_hash == content_hash,
            )
            .order_by(SourceFile.version_ref)
            .limit(1)
        )
        if source_file is None:
            return None
        chunks_result = await db.execute(
            select(CodeChunk)
            .where(CodeChunk.file_id == source_file.id)
            .order_by(CodeChunk.start_line, CodeChunk.end_line, CodeChunk.symbol_name)
        )
        embeddings_by_chunk: Dict[tuple, list] = {}
        for existing_chunk in chunks_result.scalars().all():
            embeddings_by_chunk.setdefault(_chunk_identity(existing_chunk), []).append(existing_chunk.embedding)

        reused: List[List[float]] = []
        for chunk in parsed_chunks:
            candidates = embeddings_by_chunk.get(_chunk_identity(chunk))
            if not candidates:
                return None
            embedding = candidates.pop(0)
            if embedding is None:
                return None
            reused.append(embedding)
        if any(candidates for candidates in embeddings_by_chunk.values()):
            return None
        return reused

    async def index_repository(
        self, repo_id: uuid.UUID, db: AsyncSession, version_ref: str = "default"
    ) -> None:
        """Index the default branch or an explicitly selected branch/tag."""
        stmt = select(Repository).where(Repository.id == repo_id)
        result = await db.execute(stmt)
        repo = result.scalar_one_or_none()

        if not repo:
            logger.error("Repository %s not found for indexing", repo_id)
            return

        is_default = version_ref == "default"
        if not is_default and not version_ref.startswith(("branch:", "tag:")):
            raise ValueError("Version must be 'default', 'branch:<name>', or 'tag:<name>'.")
        ref_type = "branch" if is_default else version_ref.split(":", 1)[0]
        ref_name = repo.default_branch if is_default else version_ref.split(":", 1)[1]
        version_result = await db.execute(
            select(RepositoryVersion).where(
                RepositoryVersion.repository_id == repo.id,
                RepositoryVersion.version_ref == version_ref,
            )
        )
        version = version_result.scalar_one_or_none()
        if version is None:
            version = RepositoryVersion(
                repository_id=repo.id,
                version_ref=version_ref,
                ref_type=ref_type,
                ref_name=ref_name,
                status="pending",
            )
            db.add(version)
            await db.flush()

        try:
            version.status = "indexing"
            version.error_message = None
            if is_default:
                repo.status = "indexing"
                repo.error_message = None
            await db.commit()

            # 1. Clone or pull repo
            logger.info("Cloning repository %s (%s)", repo.full_name, repo.github_url)
            github_token = settings.GITHUB_PAT
            app_auth = GitHubAppService(settings.GITHUB_APP_ID, settings.GITHUB_APP_PRIVATE_KEY, settings.GITHUB_APP_INSTALLATION_ID)
            if app_auth.configured:
                try:
                    github_token = await app_auth.installation_token()
                    logger.info("Using GitHub App installation token for %s", repo.full_name)
                except Exception:
                    logger.exception("GitHub App token exchange failed for %s", repo.full_name)
                    if not github_token:
                        raise
            clone_path = self.github_service.clone_repository(
                github_url=repo.github_url,
                pat=github_token,
                dest_dir=settings.REPOS_CLONE_DIR,
                version_ref=version_ref,
            )

            version.clone_path = clone_path
            version.commit_sha = self.github_service.current_commit(clone_path)
            if is_default:
                repo.default_branch = self.github_service.current_branch(clone_path)
                version.ref_name = repo.default_branch
                repo.clone_path = clone_path
                repo.languages = self.github_service.detect_languages(clone_path)
                repo.frameworks = self.github_service.detect_frameworks(clone_path)
            await db.commit()

            # 3. Discover source files
            discovered_files = self.github_service.list_source_files(clone_path)
            logger.info(
                "Found %d candidate source files in %s", len(discovered_files), repo.full_name
            )

            # Query existing files in DB
            existing_files_stmt = select(SourceFile).where(
                SourceFile.repository_id == repo.id,
                SourceFile.version_ref == version_ref,
            )
            existing_res = await db.execute(existing_files_stmt)
            existing_files: Dict[str, SourceFile] = {
                f.file_path: f for f in existing_res.scalars().all()
            }

            discovered_paths = set()

            for file_info in discovered_files:
                rel_path = file_info["relative_path"]
                full_path = file_info["path"]
                lang = file_info["language"]
                size = file_info["size"]
                discovered_paths.add(rel_path)

                content_hash = self.github_service.get_file_hash(full_path)
                existing_file = existing_files.get(rel_path)

                # Skip unchanged files (incremental index)
                if existing_file and existing_file.content_hash == content_hash:
                    logger.debug("Skipping unchanged file %s", rel_path)
                    continue

                # Parse file into chunks
                parsed_chunks = self.parser_service.parse_file(full_path, lang)
                if not parsed_chunks:
                    continue

                # Embed chunks
                embeddings = await self._reuse_cross_version_embeddings(
                    repo.id,
                    version_ref,
                    rel_path,
                    content_hash,
                    parsed_chunks,
                    db,
                )
                if embeddings is None:
                    embeddings = await self.embedding_service.embed_chunks(parsed_chunks)
                else:
                    logger.info("Reusing %d embeddings for unchanged file %s", len(embeddings), rel_path)

                # Count lines
                try:
                    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                        line_count = sum(1 for _ in f)
                except Exception:
                    line_count = 0

                # Upsert SourceFile record
                if existing_file:
                    existing_file.content_hash = content_hash
                    existing_file.size_bytes = size
                    existing_file.line_count = line_count
                    source_file_id = existing_file.id

                    # Delete old chunks for this file
                    del_stmt = delete(CodeChunk).where(CodeChunk.file_id == source_file_id)
                    await db.execute(del_stmt)
                else:
                    new_file = SourceFile(
                        repository_id=repo.id,
                        version_ref=version_ref,
                        file_path=rel_path,
                        language=lang,
                        size_bytes=size,
                        line_count=line_count,
                        content_hash=content_hash,
                    )
                    db.add(new_file)
                    await db.flush()
                    source_file_id = new_file.id

                # Store new CodeChunk records
                for chunk, embedding in zip(parsed_chunks, embeddings):
                    db_chunk = CodeChunk(
                        repository_id=repo.id,
                        version_ref=version_ref,
                        file_id=source_file_id,
                        file_path=rel_path,
                        language=chunk.language,
                        chunk_type=chunk.chunk_type,
                        symbol_name=chunk.symbol_name,
                        parent_symbol=chunk.parent_symbol,
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        content=chunk.content,
                        docstring=chunk.docstring,
                        imports=chunk.imports,
                        embedding=embedding,
                    )
                    db.add(db_chunk)

                await db.commit()

            # Clean up deleted files from DB that no longer exist in the repo
            for old_path, old_file in existing_files.items():
                if old_path not in discovered_paths:
                    logger.info("Cleaning up removed file %s", old_path)
                    await db.delete(old_file)

            # Update repository stats and status
            count_files_stmt = (
                select(func.count())
                .select_from(SourceFile)
                .where(SourceFile.repository_id == repo.id, SourceFile.version_ref == version_ref)
            )
            count_chunks_stmt = (
                select(func.count())
                .select_from(CodeChunk)
                .where(CodeChunk.repository_id == repo.id, CodeChunk.version_ref == version_ref)
            )

            file_count = (await db.execute(count_files_stmt)).scalar() or 0
            chunk_count = (await db.execute(count_chunks_stmt)).scalar() or 0

            version.file_count = file_count
            version.chunk_count = chunk_count
            version.status = "ready"
            version.error_message = None
            version.last_indexed_at = datetime.now(timezone.utc)
            if is_default:
                repo.file_count = file_count
                repo.chunk_count = chunk_count
                repo.status = "ready"
                repo.last_indexed_at = version.last_indexed_at
            await db.commit()

            logger.info(
                "Successfully indexed %s: %d files, %d chunks",
                repo.full_name,
                file_count,
                chunk_count,
            )

        except Exception as e:
            logger.exception("Error during indexing of repository %s ref %s: %s", repo_id, version_ref, e)
            await db.rollback()
            # Fetch fresh instance to update error status
            repo_res = await db.execute(select(Repository).where(Repository.id == repo_id))
            r = repo_res.scalar_one_or_none()
            if r:
                version_result = await db.execute(
                    select(RepositoryVersion).where(
                        RepositoryVersion.repository_id == repo_id,
                        RepositoryVersion.version_ref == version_ref,
                    )
                )
                failed_version = version_result.scalar_one_or_none()
                chunk_count_result = await db.execute(
                    select(func.count()).select_from(CodeChunk).where(
                        CodeChunk.repository_id == repo_id,
                        CodeChunk.version_ref == version_ref,
                    )
                )
                existing_chunk_count = chunk_count_result.scalar() or 0
                if _is_embedding_quota_error(e) and existing_chunk_count > 0:
                    # Keep the last complete index usable. New code will be
                    # picked up on a later retry after the provider window
                    # resets, rather than taking repository Q&A offline.
                    message = "Re-index paused because the embedding provider quota was exceeded. The previous index remains available; retry after the provider quota resets."
                    if is_default:
                        r.status = "ready"
                        r.error_message = message
                    elif failed_version:
                        # Version rows are refreshed in place, so a quota error
                        # can leave a partially updated set. Keep it unqueryable
                        # until a successful re-index completes.
                        failed_version.status = "error"
                        failed_version.error_message = "Indexing stopped because the embedding quota was reached. Retry indexing before querying this version."
                    logger.warning("Preserving previous index for %s after embedding quota exhaustion", repo_id)
                else:
                    if is_default:
                        r.status = "error"
                        r.error_message = str(e)
                    if failed_version:
                        failed_version.status = "error"
                        failed_version.error_message = (
                            "This version could not be indexed. Check that the branch or tag exists and is accessible, then retry."
                        )
                await db.commit()

    async def reindex_files(
        self, repo_id: uuid.UUID, file_paths: List[str], db: AsyncSession
    ) -> None:
        """Incrementally re-index a specific list of changed files."""
        stmt = select(Repository).where(Repository.id == repo_id)
        result = await db.execute(stmt)
        repo = result.scalar_one_or_none()

        if not repo or not repo.clone_path:
            logger.warning("Repository %s not ready for file reindexing", repo_id)
            return

        self.github_service.update_repository(repo.clone_path)

        for rel_path in file_paths:
            full_path = f"{repo.clone_path}/{rel_path}"
            ext = f".{rel_path.split('.')[-1]}" if "." in rel_path else ""
            lang = self.github_service.SUPPORTED_EXTENSIONS.get(ext)
            if not lang:
                continue

            file_stmt = select(SourceFile).where(
                SourceFile.repository_id == repo_id,
                SourceFile.file_path == rel_path,
                SourceFile.version_ref == "default",
            )
            file_res = await db.execute(file_stmt)
            existing_file = file_res.scalar_one_or_none()

            if not os.path.isfile(full_path):
                if existing_file:
                    await db.delete(existing_file)
                continue

            parsed_chunks = self.parser_service.parse_file(full_path, lang)
            if not parsed_chunks:
                continue

            embeddings = await self.embedding_service.embed_chunks(parsed_chunks)
            content_hash = self.github_service.get_file_hash(full_path)
            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as source:
                    line_count = sum(1 for _ in source)
            except OSError:
                line_count = 0
            size_bytes = os.path.getsize(full_path)

            if existing_file:
                del_stmt = delete(CodeChunk).where(CodeChunk.file_id == existing_file.id)
                await db.execute(del_stmt)
                file_id = existing_file.id
                existing_file.content_hash = content_hash
                existing_file.size_bytes = size_bytes
                existing_file.line_count = line_count
                existing_file.language = lang
            else:
                new_file = SourceFile(
                    repository_id=repo_id,
                    version_ref="default",
                    file_path=rel_path,
                    language=lang,
                    size_bytes=size_bytes,
                    line_count=line_count,
                    content_hash=content_hash,
                )
                db.add(new_file)
                await db.flush()
                file_id = new_file.id

            for chunk, embedding in zip(parsed_chunks, embeddings):
                db.add(
                    CodeChunk(
                        repository_id=repo_id,
                        version_ref="default",
                        file_id=file_id,
                        file_path=rel_path,
                        language=chunk.language,
                        chunk_type=chunk.chunk_type,
                        symbol_name=chunk.symbol_name,
                        parent_symbol=chunk.parent_symbol,
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        content=chunk.content,
                        docstring=chunk.docstring,
                        imports=chunk.imports,
                        embedding=embedding,
                    )
                )

        count_files = await db.scalar(
            select(func.count()).select_from(SourceFile).where(
                SourceFile.repository_id == repo_id,
                SourceFile.version_ref == "default",
            )
        ) or 0
        count_chunks = await db.scalar(
            select(func.count()).select_from(CodeChunk).where(
                CodeChunk.repository_id == repo_id,
                CodeChunk.version_ref == "default",
            )
        ) or 0
        now = datetime.now(timezone.utc)
        repo.file_count = count_files
        repo.chunk_count = count_chunks
        repo.last_indexed_at = now
        version = await db.scalar(
            select(RepositoryVersion).where(
                RepositoryVersion.repository_id == repo_id,
                RepositoryVersion.version_ref == "default",
            )
        )
        if version:
            version.file_count = count_files
            version.chunk_count = count_chunks
            version.commit_sha = self.github_service.current_commit(repo.clone_path)
            version.last_indexed_at = now
            version.status = "ready"
            version.error_message = None
        await db.commit()
