"""Associate repositories with their creating users."""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004_repository_owners"
down_revision: Union[str, None] = "003_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("repositories")}
    if "owner_id" in columns:
        return
    op.add_column("repositories", sa.Column("owner_id", sa.UUID(), nullable=True))
    op.create_index(op.f("ix_repositories_owner_id"), "repositories", ["owner_id"], unique=False)
    op.create_foreign_key("fk_repositories_owner_id_users", "repositories", "users", ["owner_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_repositories_owner_id_users", "repositories", type_="foreignkey")
    op.drop_index(op.f("ix_repositories_owner_id"), table_name="repositories")
    op.drop_column("repositories", "owner_id")
