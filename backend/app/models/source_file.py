import uuid
from datetime import datetime
from sqlalchemy import Index, String, DateTime, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class SourceFile(Base):
    """A source file within an indexed repository."""

    __tablename__ = "source_files"
    __table_args__ = (Index("ix_source_files_repository_version", "repository_id", "version_ref"),)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, index=True
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    version_ref: Mapped[str] = mapped_column(String(255), nullable=False, default="default", index=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    line_count: Mapped[int] = mapped_column(Integer, default=0)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationship back to repo (lazy loaded)
    repository = relationship("Repository", back_populates=None, lazy="select")
