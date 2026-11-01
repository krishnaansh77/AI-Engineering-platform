"""Backfill repository summary counters for legacy indexed rows."""
from typing import Sequence, Union

from alembic import op


revision: str = "008_backfill_repository_stats"
down_revision: Union[str, None] = "007_query_token_usage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Older deployments populated source_files/code_chunks before the summary
    # counters were maintained. Recompute them from the source of truth so the
    # dashboard and repository detail page cannot report misleading zeros.
    op.execute(
        """
        UPDATE repositories AS r
        SET file_count = (
                SELECT COUNT(*)
                FROM source_files AS sf
                WHERE sf.repository_id = r.id
            ),
            chunk_count = (
                SELECT COUNT(*)
                FROM code_chunks AS cc
                WHERE cc.repository_id = r.id
            )
        """
    )
    op.execute(
        """
        UPDATE repositories AS r
        SET last_indexed_at = COALESCE(
            (
                SELECT MAX(sf.created_at)
                FROM source_files AS sf
                WHERE sf.repository_id = r.id
            ),
            r.created_at
        )
        WHERE r.status = 'ready' AND r.last_indexed_at IS NULL
        """
    )


def downgrade() -> None:
    # The original counter values cannot be reconstructed safely. Keeping the
    # corrected aggregates is safer than reverting them to misleading zeros.
    pass
