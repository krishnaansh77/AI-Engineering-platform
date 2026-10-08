"""Validation tests for the CI-friendly RAG benchmark runner."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_rag_benchmark import load_benchmark


class TestBenchmarkRunner(unittest.TestCase):
    def write_payload(self, payload):
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        with handle:
            json.dump(payload, handle)
        return Path(handle.name)

    def test_loads_and_normalizes_default_top_k(self):
        path = self.write_payload(
            {"cases": [{"question": "Where is the API?", "expected_files": ["api.py"]}]}
        )
        self.assertEqual(load_benchmark(path)["top_k"], 5)

    def test_rejects_invalid_top_k(self):
        path = self.write_payload(
            {"top_k": 0, "cases": [{"question": "Q", "expected_files": ["a.py"]}]}
        )
        with self.assertRaisesRegex(ValueError, "top_k"):
            load_benchmark(path)

    def test_rejects_empty_expected_files(self):
        path = self.write_payload(
            {"cases": [{"question": "Q", "expected_files": []}]}
        )
        with self.assertRaisesRegex(ValueError, "expected_files"):
            load_benchmark(path)


if __name__ == "__main__":
    unittest.main()
