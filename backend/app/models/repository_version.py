"""Indexed branch and tag metadata for a repository."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RepositoryVersion(Base):
    """Index status and isolated checkout location for one repository ref."""

    __tablename__ = "repository_versions"
    __table_args__ = (UniqueConstraint("repository_id", "version_ref", name="uq_repository_versions_repo_ref"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # `default` identifies the repository's configured default branch. Other
    # values use `branch:<name>` or `tag:<name>` to avoid name collisions.
    version_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    ref_type: Mapped[str] = mapped_column(String(20), nullable=False)
    ref_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    commit_sha: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    clone_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
