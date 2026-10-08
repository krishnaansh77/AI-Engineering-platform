"""Add explicit multi-repository workspaces."""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "005_workspaces"
down_revision: Union[str, None] = "004_repository_owners"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "workspaces" not in tables:
        op.create_table(
            "workspaces",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("slug", sa.String(length=100), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("slug"),
        )
        op.create_index(op.f("ix_workspaces_id"), "workspaces", ["id"], unique=False)
        op.create_index(op.f("ix_workspaces_slug"), "workspaces", ["slug"], unique=False)
    if "workspace_members" not in tables:
        op.create_table(
            "workspace_members",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("workspace_id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("role", sa.String(length=30), server_default="member", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
        )
        op.create_index(op.f("ix_workspace_members_id"), "workspace_members", ["id"], unique=False)
        op.create_index(op.f("ix_workspace_members_workspace_id"), "workspace_members", ["workspace_id"], unique=False)
        op.create_index(op.f("ix_workspace_members_user_id"), "workspace_members", ["user_id"], unique=False)
    columns = {column["name"] for column in inspector.get_columns("repositories")}
    if "workspace_id" not in columns:
        op.add_column("repositories", sa.Column("workspace_id", sa.UUID(), nullable=True))
        op.create_index(op.f("ix_repositories_workspace_id"), "repositories", ["workspace_id"], unique=False)
        op.create_foreign_key("fk_repositories_workspace_id_workspaces", "repositories", "workspaces", ["workspace_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_repositories_workspace_id_workspaces", "repositories", type_="foreignkey")
    op.drop_index(op.f("ix_repositories_workspace_id"), table_name="repositories")
    op.drop_column("repositories", "workspace_id")
    op.drop_table("workspace_members")
    op.drop_table("workspaces")
