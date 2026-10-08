import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, DateTime, JSON, Integer, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Repository(Base):
    """A connected GitHub repository."""

    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    github_url: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    clone_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Detected metadata
    languages: Mapped[List[str]] = mapped_column(JSON, default=list)
    frameworks: Mapped[List[str]] = mapped_column(JSON, default=list)

    # Indexing status: pending | indexing | ready | error
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Stats
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    last_indexed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # GitHub webhook
    github_webhook_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )

    # Nullable during migration so existing repositories remain usable.
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    workspace_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True
    )
