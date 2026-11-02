"""Exercise the version migration on a small legacy SQLite schema."""
import importlib.util
import uuid
import unittest
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


class TestRepositoryVersionMigration(unittest.TestCase):
    def test_backfills_default_version_and_adds_scoping_columns(self):
        migration_path = Path(__file__).parents[1] / "alembic" / "versions" / "009_repository_versions.py"
        spec = importlib.util.spec_from_file_location("repository_version_migration", migration_path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)

        engine = sa.create_engine("sqlite:///:memory:")
        repository_id = uuid.uuid4()
        with engine.begin() as connection:
            metadata = sa.MetaData()
            sa.Table(
                "repositories", metadata,
                sa.Column("id", sa.UUID(), primary_key=True),
                sa.Column("default_branch", sa.String(100)),
                sa.Column("status", sa.String(20)),
                sa.Column("clone_path", sa.String(512)),
                sa.Column("file_count", sa.Integer()),
                sa.Column("chunk_count", sa.Integer()),
                sa.Column("error_message", sa.Text()),
                sa.Column("last_indexed_at", sa.DateTime(timezone=True)),
            )
            sa.Table(
                "source_files", metadata,
                sa.Column("id", sa.UUID(), primary_key=True),
                sa.Column("repository_id", sa.UUID()),
            )
            sa.Table(
                "code_chunks", metadata,
                sa.Column("id", sa.UUID(), primary_key=True),
                sa.Column("repository_id", sa.UUID()),
            )
            metadata.create_all(connection)
            connection.execute(
                sa.text(
                    "INSERT INTO repositories "
                    "(id, default_branch, status, clone_path, file_count, chunk_count) "
                    "VALUES (:id, 'release', 'ready', '/repos/demo', 4, 9)"
                ),
                {"id": str(repository_id)},
            )

            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()

            version = connection.execute(
                sa.text(
                    "SELECT version_ref, ref_type, ref_name, status, clone_path, file_count, chunk_count "
                    "FROM repository_versions"
                )
            ).one()
            self.assertEqual(version, ("default", "branch", "release", "ready", "/repos/demo", 4, 9))
            self.assertIn("version_ref", {column["name"] for column in sa.inspect(connection).get_columns("source_files")})
            self.assertIn("version_ref", {column["name"] for column in sa.inspect(connection).get_columns("code_chunks")})

        engine.dispose()


if __name__ == "__main__":
    unittest.main()
