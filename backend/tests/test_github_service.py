"""Unit tests for GitHubService methods."""
import hashlib
import hmac
import os
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
