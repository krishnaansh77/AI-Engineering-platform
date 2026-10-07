import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, DateTime, Integer, Text, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.database import Base
from app.config import settings


class CodeChunk(Base):
    """A semantically meaningful chunk of code with its embedding vector."""

    __tablename__ = "code_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, index=True
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_files.id", ondelete="CASCADE"), index=True
    )

    # Denormalized for fast retrieval without joins
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(50), nullable=False)

    # Chunk classification
    # "function" | "class" | "method" | "module" | "other"
    chunk_type: Mapped[str] = mapped_column(String(20), nullable=False)
    symbol_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    parent_symbol: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Source location
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    docstring: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    imports: Mapped[List[str]] = mapped_column(JSON, default=list)

    # Vector embedding (pgvector)
    embedding: Mapped[Optional[List[float]]] = mapped_column(
        Vector(settings.EMBEDDING_DIMENSION), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
