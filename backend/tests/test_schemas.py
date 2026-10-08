"""Unit tests for Pydantic schemas and serialization."""
import unittest
import uuid
from datetime import datetime, timezone
from app.api.schemas import (
    ConnectRepoRequest,
    RepositoryResponse,
    RepoStatsResponse,
    CitationSchema,
    QueryRequest,
    QueryResponse,
)
from app.api.errors import error_detail


class TestSchemas(unittest.TestCase):
    def test_connect_repo_request_validation(self):
        req = ConnectRepoRequest(github_url="https://github.com/tiangolo/fastapi")
        self.assertEqual(req.github_url, "https://github.com/tiangolo/fastapi")
        self.assertIsNone(req.name)

        req_with_name = ConnectRepoRequest(
            github_url="https://github.com/tiangolo/fastapi", name="FastAPI"
        )
        self.assertEqual(req_with_name.name, "FastAPI")

    def test_repository_response(self):
        repo_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        data = {
            "id": repo_id,
            "name": "fastapi",
            "full_name": "tiangolo/fastapi",
            "github_url": "https://github.com/tiangolo/fastapi",
            "description": "FastAPI framework",
            "default_branch": "main",
            "status": "ready",
            "error_message": None,
            "languages": ["python"],
            "frameworks": ["FastAPI"],
            "file_count": 120,
            "chunk_count": 450,
            "last_indexed_at": now,
            "created_at": now,
        }
        res = RepositoryResponse(**data)
        self.assertEqual(res.id, repo_id)
        self.assertEqual(res.status, "ready")
        self.assertEqual(res.file_count, 120)

    def test_query_request_validation(self):
        req = QueryRequest(question="Where is auth?", top_k=8)
        self.assertEqual(req.question, "Where is auth?")
        self.assertEqual(req.top_k, 8)

    def test_query_response(self):
        citation = CitationSchema(
            file_path="src/auth.py",
            symbol_name="login",
            chunk_type="function",
            start_line=10,
            end_line=25,
        )
        res = QueryResponse(
            answer="Login is implemented in login()",
            citations=[citation],
            model="gpt-4o",
            retrieval_count=1,
        )
        self.assertEqual(len(res.citations), 1)
        self.assertEqual(res.citations[0].symbol_name, "login")

    def test_error_detail_is_structured(self):
        self.assertEqual(
            error_detail("RATE_LIMITED", "Try again", True),
            {"error": {"code": "RATE_LIMITED", "message": "Try again", "retryable": True}},
        )


if __name__ == "__main__":
    unittest.main()
