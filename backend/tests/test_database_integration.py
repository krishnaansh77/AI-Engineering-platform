"""Database-backed endpoint smoke tests.

Run with RUN_DB_INTEGRATION=1 and a PostgreSQL/pgvector DATABASE_URL.
The regular local suite skips these tests when no database is configured.
"""
import os
import unittest
import uuid
from datetime import datetime, timezone
from importlib.util import find_spec

DB_INTEGRATION_ENABLED = os.getenv("RUN_DB_INTEGRATION") == "1" and find_spec("fastapi") is not None
if DB_INTEGRATION_ENABLED:
    from app.api.query import evaluate_repository_retrieval
    from app.api.schemas import EvaluationCase, EvaluationRequest
    from app.database import AsyncSessionLocal, create_all_tables, engine
    from app.models.code_chunk import CodeChunk
    from app.models.repository import Repository
    from app.models.source_file import SourceFile
    from app.providers.embedding.mock_embedding import MockEmbeddingProvider


@unittest.skipUnless(DB_INTEGRATION_ENABLED, "set RUN_DB_INTEGRATION=1 to run database integration tests")
class TestDatabaseIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await create_all_tables()
        self.repo_id = uuid.uuid4()
        self.file_id = uuid.uuid4()
        provider = MockEmbeddingProvider()
        async with AsyncSessionLocal() as session:
            session.add(Repository(
                id=self.repo_id,
                name="integration-fixture",
                full_name=f"integration/{self.repo_id}",
                github_url="https://github.com/integration/fixture",
                status="ready",
                languages=["python"],
                frameworks=[],
                file_count=1,
                chunk_count=1,
                last_indexed_at=datetime.now(timezone.utc),
            ))
            session.add(SourceFile(
                id=self.file_id,
                repository_id=self.repo_id,
                file_path="backend/app/database.py",
                language="python",
                size_bytes=64,
                line_count=1,
                content_hash=uuid.uuid4().hex,
            ))
            content = "database initialization creates the SQLAlchemy async engine"
            session.add(CodeChunk(
                repository_id=self.repo_id,
                file_id=self.file_id,
                file_path="backend/app/database.py",
                language="python",
                chunk_type="module",
                symbol_name="database",
                start_line=1,
                end_line=1,
                content=content,
                imports=[],
                embedding=await provider.embed_single(content),
            ))
            await session.commit()

    async def asyncTearDown(self):
        async with AsyncSessionLocal() as session:
            repository = await session.get(Repository, self.repo_id)
            if repository:
                await session.delete(repository)
                await session.commit()
        await engine.dispose()

    async def test_evaluation_endpoint_reads_pgvector_repository(self):
        payload = EvaluationRequest(
            cases=[EvaluationCase(
                question="How is the database initialized?",
                expected_files=["backend/app/database.py"],
            )],
            top_k=3,
        )
        async with AsyncSessionLocal() as session:
            result = await evaluate_repository_retrieval(self.repo_id, payload, session)
        self.assertEqual(result["summary"]["case_count"], 1)
        self.assertEqual(result["summary"]["recall_at_k"], 1.0)
        self.assertEqual(result["cases"][0]["matched_files"], ["backend/app/database.py"])


if __name__ == "__main__":
    unittest.main()
