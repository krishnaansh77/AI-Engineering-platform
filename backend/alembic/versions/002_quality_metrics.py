"""Persist citation counts for answer quality reporting."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_quality_metrics"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("query_events", sa.Column("citation_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("query_feedback", sa.Column("citation_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("query_feedback", "citation_count")
    op.drop_column("query_events", "citation_count")
