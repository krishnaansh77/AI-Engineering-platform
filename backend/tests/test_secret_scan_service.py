"""Tests for the opt-in redacting secret heuristic."""
import tempfile
import unittest
from pathlib import Path

from app.services.secret_scan_service import SecretScanService


class TestSecretScanService(unittest.TestCase):
    def test_finds_and_redacts_api_key_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.py"
            path.write_text('api_key = "super-secret-value-123"\n')
            result = SecretScanService().scan(directory, [{"path": str(path), "relative_path": "config.py"}])
            self.assertEqual(result["finding_count"], 1)
            self.assertNotIn("super-secret-value-123", result["findings"][0]["redacted_preview"])
            self.assertEqual(result["findings"][0]["line"], 1)

    def test_marks_scan_as_heuristic(self):
        result = SecretScanService().scan("/tmp", [])
        self.assertTrue(result["heuristic"])
