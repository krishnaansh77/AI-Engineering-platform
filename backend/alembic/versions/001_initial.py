"""Initial schema with pgvector extension and core models

Revision ID: 001_initial
Revises: 
Create Date: 2026-09-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create repositories table
    op.create_table(
        "repositories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("github_url", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_branch", sa.String(length=100), server_default="main", nullable=False),
        sa.Column("clone_path", sa.String(length=512), nullable=True),
        sa.Column("languages", sa.JSON(), nullable=False),
        sa.Column("frameworks", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("file_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("github_webhook_id", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("full_name"),
    )
    op.create_index(op.f("ix_repositories_id"), "repositories", ["id"], unique=False)
    op.create_index(op.f("ix_repositories_status"), "repositories", ["status"], unique=False)

    # Create source_files table
    op.create_table(
        "source_files",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("repository_id", sa.UUID(), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("language", sa.String(length=50), nullable=False),
        sa.Column("size_bytes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("line_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_source_files_id"), "source_files", ["id"], unique=False)
    op.create_index(op.f("ix_source_files_repository_id"), "source_files", ["repository_id"], unique=False)

    # Create code_chunks table
    op.create_table(
        "code_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("repository_id", sa.UUID(), nullable=False),
        sa.Column("file_id", sa.UUID(), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("language", sa.String(length=50), nullable=False),
        sa.Column("chunk_type", sa.String(length=20), nullable=False),
        sa.Column("symbol_name", sa.String(length=255), nullable=True),
        sa.Column("parent_symbol", sa.String(length=255), nullable=True),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("docstring", sa.Text(), nullable=True),
        sa.Column("imports", sa.JSON(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["source_files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_code_chunks_id"), "code_chunks", ["id"], unique=False)
    op.create_index(op.f("ix_code_chunks_file_id"), "code_chunks", ["file_id"], unique=False)
    op.create_index(op.f("ix_code_chunks_file_path"), "code_chunks", ["file_path"], unique=False)
    op.create_index(op.f("ix_code_chunks_repository_id"), "code_chunks", ["repository_id"], unique=False)
    op.create_index(op.f("ix_code_chunks_symbol_name"), "code_chunks", ["symbol_name"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_code_chunks_symbol_name"), table_name="code_chunks")
    op.drop_index(op.f("ix_code_chunks_repository_id"), table_name="code_chunks")
    op.drop_index(op.f("ix_code_chunks_file_path"), table_name="code_chunks")
    op.drop_index(op.f("ix_code_chunks_file_id"), table_name="code_chunks")
    op.drop_index(op.f("ix_code_chunks_id"), table_name="code_chunks")
    op.drop_table("code_chunks")

    op.drop_index(op.f("ix_source_files_repository_id"), table_name="source_files")
    op.drop_index(op.f("ix_source_files_id"), table_name="source_files")
    op.drop_table("source_files")

    op.drop_index(op.f("ix_repositories_status"), table_name="repositories")
    op.drop_index(op.f("ix_repositories_id"), table_name="repositories")
    op.drop_table("repositories")
