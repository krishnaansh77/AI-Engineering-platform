"""Persist provider token usage for query observability."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "007_query_token_usage"
down_revision: Union[str, None] = "006_workspace_invitations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("query_events", sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("query_events", sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("query_events", "completion_tokens")
    op.drop_column("query_events", "prompt_tokens")
