"""Tests for repository version validation and retrieval isolation."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.api.schemas import QueryRequest, RepositoryVersionIndexRequest
from app.services.retrieval_service import RetrievalService
from app.services.indexing_service import IndexingService
from app.services.parser_service import ParsedChunk


class EmptyResult:
    def scalars(self):
        return self

    def all(self):
        return []


class CapturingSession:
    def __init__(self):
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return EmptyResult()


class TestVersionValidation(unittest.TestCase):
    def test_query_defaults_to_default_version(self):
        self.assertEqual(QueryRequest(question="Where is login?").version_ref, "default")

    def test_query_accepts_branch_and_tag_refs(self):
        self.assertEqual(QueryRequest(question="Where is login?", version_ref="branch:feature/login").version_ref, "branch:feature/login")
        self.assertEqual(RepositoryVersionIndexRequest(ref_type="tag", ref_name="v1.2.0").ref_name, "v1.2.0")

    def test_invalid_git_refs_are_rejected(self):
        for version_ref in (
            "branch:../private",
            "tag:release.lock",
            "branch:feature//broken",
            "branch:feature/.hidden",
            "branch:feature/a..b",
            "branch:feature./subtree",
        ):
            with self.subTest(version_ref=version_ref), self.assertRaises(ValueError):
                QueryRequest(question="Where is login?", version_ref=version_ref)


class TestRetrievalVersionIsolation(unittest.IsolatedAsyncioTestCase):
    async def test_candidate_query_is_scoped_to_requested_version(self):
        session = CapturingSession()
        await RetrievalService().retrieve(
            query="Where is login?",
            repo_id="00000000-0000-0000-0000-000000000001",
            db=session,
            version_ref="branch:feature/login",
        )
        statement = session.statements[0]
        self.assertIn("code_chunks.version_ref", str(statement))
        self.assertIn("branch:feature/login", statement.compile().params.values())


class TestCrossVersionEmbeddingReuse(unittest.IsolatedAsyncioTestCase):
    async def test_reuses_vectors_only_when_every_chunk_matches(self):
        embedding = [0.25] * 768
        stored_chunk = SimpleNamespace(
            chunk_type="function",
            symbol_name="login",
            parent_symbol=None,
            start_line=1,
            end_line=2,
            content="def login(): return True",
            embedding=embedding,
        )

        class FakeSession:
            async def scalar(self, _statement):
                return SimpleNamespace(id="stored-file")

            async def execute(self, _statement):
                class Result:
                    def scalars(self):
                        return self

                    def all(self):
                        return [stored_chunk]

                return Result()

        parsed = ParsedChunk(
            "function", "login", None, 1, 2, "def login(): return True", None, [], "python"
        )
        service = IndexingService(embedding_service=SimpleNamespace(embed_chunks=AsyncMock()))
        reused = await service._reuse_cross_version_embeddings(
            repo_id="00000000-0000-0000-0000-000000000001",
            version_ref="branch:feature/login",
            file_path="auth.py",
            content_hash="same-content",
            parsed_chunks=[parsed],
            db=FakeSession(),
        )

        self.assertEqual(reused, [embedding])

    async def test_reembeds_if_chunk_identity_does_not_match(self):
        stored_chunk = SimpleNamespace(
            chunk_type="function",
            symbol_name="old_login",
            parent_symbol=None,
            start_line=1,
            end_line=2,
            content="def old_login(): return True",
            embedding=[0.25] * 768,
        )

        class FakeSession:
            async def scalar(self, _statement):
                return SimpleNamespace(id="stored-file")

            async def execute(self, _statement):
                class Result:
                    def scalars(self):
                        return self

                    def all(self):
                        return [stored_chunk]

                return Result()

        parsed = ParsedChunk(
            "function", "login", None, 1, 2, "def login(): return True", None, [], "python"
        )
        service = IndexingService()
        reused = await service._reuse_cross_version_embeddings(
            repo_id="00000000-0000-0000-0000-000000000001",
            version_ref="tag:v1.0",
            file_path="auth.py",
            content_hash="same-content",
            parsed_chunks=[parsed],
            db=FakeSession(),
        )

        self.assertIsNone(reused)


if __name__ == "__main__":
    unittest.main()
