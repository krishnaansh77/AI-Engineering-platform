"""Tests for Git history serialization."""
import tempfile
import unittest
from pathlib import Path

import git

from app.services.github_service import GitHubService


class TestGitHubHistory(unittest.TestCase):
    def test_reads_recent_commit_metadata_and_changed_files(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = git.Repo.init(directory)
            path = Path(directory) / "hello.py"
            path.write_text("print('hello')\n")
            repo.index.add([str(path)])
            repo.index.commit("Add hello module")

            history = GitHubService().get_commit_history(directory, limit=5)

            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["message"], "Add hello module")
            self.assertEqual(history[0]["files"], ["hello.py"])
            self.assertEqual(history[0]["files_changed"], 1)

    def test_source_reader_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                GitHubService().read_source_file(directory, "../outside.py")

    def test_lists_documentation_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "README.md"
            path.write_text("# Project\n")
            docs = GitHubService().list_documentation_files(directory)
            self.assertEqual(docs[0]["file_path"], "README.md")
            self.assertIn("Project", docs[0]["content"])

    def test_analyzes_latest_commit_file_categories(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = git.Repo.init(directory)
            path = Path(directory) / "service.py"
            path.write_text("print('one')\n")
            repo.index.add([str(path)])
            repo.index.commit("Add service")
            analysis = GitHubService().analyze_latest_commit(directory)
            self.assertEqual(analysis["source_files"], ["service.py"])
            self.assertTrue(analysis["recommendations"])


if __name__ == "__main__":
    unittest.main()
