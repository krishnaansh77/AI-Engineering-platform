"""Add branch/tag-scoped repository indexes."""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "009_repository_versions"
down_revision: Union[str, None] = "008_backfill_repository_stats"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "source_files",
        sa.Column("version_ref", sa.String(length=255), server_default="default", nullable=False),
    )
    op.add_column(
        "code_chunks",
        sa.Column("version_ref", sa.String(length=255), server_default="default", nullable=False),
    )
    op.create_index("ix_source_files_version_ref", "source_files", ["version_ref"])
    op.create_index("ix_code_chunks_version_ref", "code_chunks", ["version_ref"])
    op.create_index(
        "ix_source_files_repository_version",
        "source_files",
        ["repository_id", "version_ref"],
    )
    op.create_index(
        "ix_code_chunks_repository_version",
        "code_chunks",
        ["repository_id", "version_ref"],
    )
    op.create_table(
        "repository_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("repository_id", sa.UUID(), nullable=False),
        sa.Column("version_ref", sa.String(length=255), nullable=False),
        sa.Column("ref_type", sa.String(length=20), nullable=False),
        sa.Column("ref_name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("commit_sha", sa.String(length=40), nullable=True),
        sa.Column("clone_path", sa.String(length=512), nullable=True),
        sa.Column("file_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "version_ref", name="uq_repository_versions_repo_ref"),
    )
    op.create_index("ix_repository_versions_id", "repository_versions", ["id"])
    op.create_index("ix_repository_versions_repository_id", "repository_versions", ["repository_id"])
    op.create_index("ix_repository_versions_status", "repository_versions", ["status"])

    bind = op.get_bind()
    rows = list(bind.execute(
        sa.text(
            "SELECT id, default_branch, status, clone_path, file_count, chunk_count, "
            "error_message, last_indexed_at FROM repositories"
        )
    ).mappings())
    versions = sa.table(
        "repository_versions",
        sa.column("id", sa.UUID()),
        sa.column("repository_id", sa.UUID()),
        sa.column("version_ref", sa.String()),
        sa.column("ref_type", sa.String()),
        sa.column("ref_name", sa.String()),
        sa.column("status", sa.String()),
        sa.column("clone_path", sa.String()),
        sa.column("file_count", sa.Integer()),
        sa.column("chunk_count", sa.Integer()),
        sa.column("error_message", sa.Text()),
        sa.column("last_indexed_at", sa.DateTime(timezone=True)),
    )
    for row in rows:
        bind.execute(
            versions.insert().values(
                id=uuid.uuid4(),
                repository_id=(
                    row["id"] if isinstance(row["id"], uuid.UUID) else uuid.UUID(str(row["id"]))
                ),
                version_ref="default",
                ref_type="branch",
                ref_name=row["default_branch"] or "main",
                status=row["status"] or "pending",
                clone_path=row["clone_path"],
                file_count=row["file_count"] or 0,
                chunk_count=row["chunk_count"] or 0,
                error_message=row["error_message"],
                last_indexed_at=row["last_indexed_at"],
            )
        )


def downgrade() -> None:
    op.drop_index("ix_repository_versions_status", table_name="repository_versions")
    op.drop_index("ix_repository_versions_repository_id", table_name="repository_versions")
    op.drop_index("ix_repository_versions_id", table_name="repository_versions")
    op.drop_table("repository_versions")
    op.drop_index("ix_code_chunks_repository_version", table_name="code_chunks")
    op.drop_index("ix_source_files_repository_version", table_name="source_files")
    op.drop_index("ix_code_chunks_version_ref", table_name="code_chunks")
    op.drop_index("ix_source_files_version_ref", table_name="source_files")
    op.drop_column("code_chunks", "version_ref")
    op.drop_column("source_files", "version_ref")
