"""Unit tests for GitHubService methods."""
import hashlib
import hmac
import os
import tempfile
import unittest
import asyncio
import base64
from unittest.mock import AsyncMock, patch
from app.services.github_service import GitHubService


class TestGitHubService(unittest.TestCase):
    def setUp(self):
        self.service = GitHubService()

    def test_file_hash(self):
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write("def hello():\n    return 'world'\n")
            f_path = f.name

        try:
            expected_hash = hashlib.sha256(
                b"def hello():\n    return 'world'\n"
            ).hexdigest()
            actual_hash = self.service.get_file_hash(f_path)
            self.assertEqual(actual_hash, expected_hash)
        finally:
            os.remove(f_path)

    def test_detect_frameworks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create package.json and requirements.txt
            with open(os.path.join(tmpdir, "package.json"), "w") as f:
                f.write("{}")
            with open(os.path.join(tmpdir, "requirements.txt"), "w") as f:
                f.write("fastapi\n")

            frameworks = self.service.detect_frameworks(tmpdir)
            self.assertIn("Node.js", frameworks)
            self.assertIn("Python", frameworks)

    def test_detect_languages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create sample files
            with open(os.path.join(tmpdir, "index.ts"), "w") as f:
                f.write("const x: number = 1;")
            with open(os.path.join(tmpdir, "main.py"), "w") as f:
                f.write("print('hi')")
            with open(os.path.join(tmpdir, "app.py"), "w") as f:
                f.write("print('app')")

            languages = self.service.detect_languages(tmpdir)
            # Python has 2 files, TypeScript has 1
            self.assertEqual(languages, ["python", "typescript"])

    def test_verify_webhook_signature(self):
        secret = "test_webhook_secret_key"
        payload = b'{"action": "push", "repository": {"name": "test"}}'
        computed = hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        valid_header = f"sha256={computed}"
        invalid_header = "sha256=invalidhexstring"

        self.assertTrue(
            self.service.verify_webhook_signature(payload, valid_header, secret)
        )
        self.assertFalse(
            self.service.verify_webhook_signature(payload, invalid_header, secret)
        )
        self.assertFalse(
            self.service.verify_webhook_signature(payload, "bad_format", secret)
        )

    def test_list_issues_rejects_unknown_state(self):
        with self.assertRaises(ValueError):
            import asyncio
            asyncio.run(self.service.list_issues("https://github.com/acme/demo", state="unknown"))

    def test_list_issues_filters_pull_requests(self):
        import asyncio

        response = unittest.mock.Mock(status_code=200)
        response.json.return_value = [
            {"number": 1, "title": "Bug", "body": "Details", "html_url": "https://github.com/acme/demo/issues/1", "labels": [], "created_at": "2026-01-01T00:00:00Z"},
            {"number": 2, "title": "PR", "body": "", "html_url": "https://github.com/acme/demo/pull/2", "labels": [], "created_at": "2026-01-01T00:00:00Z", "pull_request": {"url": "x"}},
        ]
        response.raise_for_status = unittest.mock.Mock()

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_):
                return None

            get = AsyncMock(return_value=response)

        with patch("app.services.github_service.httpx.AsyncClient", return_value=FakeClient()):
            issues = asyncio.run(self.service.list_issues("https://github.com/acme/demo", state="all"))

        self.assertEqual([issue["number"] for issue in issues], [1])
        FakeClient.get.assert_awaited_once()
        self.assertEqual(FakeClient.get.await_args.kwargs["params"]["state"], "all")

    def test_list_issues_retries_transient_server_error(self):
        retry_response = unittest.mock.Mock(status_code=503)
        retry_response.raise_for_status = unittest.mock.Mock(side_effect=Exception("temporary"))
        success_response = unittest.mock.Mock(status_code=200)
        success_response.raise_for_status = unittest.mock.Mock()
        success_response.json.return_value = []

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_):
                return None

            get = AsyncMock(side_effect=[retry_response, success_response])

        with patch("app.services.github_service.httpx.AsyncClient", return_value=FakeClient()), patch("app.services.github_service.asyncio.sleep", new=AsyncMock()):
            issues = asyncio.run(self.service.list_issues("https://github.com/acme/demo"))

        self.assertEqual(issues, [])
        self.assertEqual(FakeClient.get.await_count, 2)

    def test_documentation_save_returns_diff_without_mutating(self):
        existing = "# Old docs\n"
        response = unittest.mock.Mock(status_code=200)
        response.json.return_value = {
            "sha": "old-sha",
            "content": base64.b64encode(existing.encode()).decode(),
        }
        response.raise_for_status = unittest.mock.Mock()

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_):
                return None

            get = AsyncMock(return_value=response)
            put = AsyncMock()

        with patch("app.services.github_service.httpx.AsyncClient", return_value=FakeClient()):
            result = asyncio.run(self.service.save_documentation_file(
                "https://github.com/acme/demo", "pat", "docs/README.md", "# New docs\n", "main", "Update docs"
            ))

        self.assertFalse(result["saved"])
        self.assertTrue(result["changed"])
        self.assertIn("-# Old docs", result["diff"])
        self.assertIn("+# New docs", result["diff"])
        FakeClient.put.assert_not_awaited()

    def test_documentation_save_commits_only_after_confirmation(self):
        response = unittest.mock.Mock(status_code=404)
        response.raise_for_status = unittest.mock.Mock()
        saved_response = unittest.mock.Mock(status_code=201)
        saved_response.raise_for_status = unittest.mock.Mock()
        saved_response.json.return_value = {"commit": {"sha": "new-sha", "html_url": "https://github.com/acme/demo/commit/new-sha"}}

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_):
                return None

            get = AsyncMock(return_value=response)
            put = AsyncMock(return_value=saved_response)

        with patch("app.services.github_service.httpx.AsyncClient", return_value=FakeClient()):
            result = asyncio.run(self.service.save_documentation_file(
                "https://github.com/acme/demo", "pat", "docs/README.md", "# New docs\n", "main", "Add docs", True
            ))

        self.assertTrue(result["saved"])
        self.assertEqual(result["commit_sha"], "new-sha")
        body = FakeClient.put.await_args.kwargs["json"]
        self.assertEqual(body["branch"], "main")
        self.assertEqual(body["content"], base64.b64encode(b"# New docs\n").decode())


if __name__ == "__main__":
    unittest.main()
