"""Add expiring workspace invitations."""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "006_workspace_invitations"
down_revision: Union[str, None] = "005_workspaces"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if "workspace_invitations" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "workspace_invitations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("invited_by", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role", sa.String(length=30), server_default="member", nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("token_hash"),
        sa.UniqueConstraint("workspace_id", "email", "accepted_at", name="uq_active_workspace_invitation"),
    )
    op.create_index(op.f("ix_workspace_invitations_id"), "workspace_invitations", ["id"], unique=False)
    op.create_index(op.f("ix_workspace_invitations_workspace_id"), "workspace_invitations", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_workspace_invitations_invited_by"), "workspace_invitations", ["invited_by"], unique=False)
    op.create_index(op.f("ix_workspace_invitations_email"), "workspace_invitations", ["email"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_workspace_invitations_email"), table_name="workspace_invitations")
    op.drop_index(op.f("ix_workspace_invitations_invited_by"), table_name="workspace_invitations")
    op.drop_index(op.f("ix_workspace_invitations_workspace_id"), table_name="workspace_invitations")
    op.drop_index(op.f("ix_workspace_invitations_id"), table_name="workspace_invitations")
    op.drop_table("workspace_invitations")
