"""Tests for package identity/dependency extraction used by the workspace map."""
import tempfile
import unittest
from pathlib import Path

from app.services.cross_repo_impact import repository_packages


class TestRepositoryPackages(unittest.TestCase):
    def test_reads_and_normalizes_node_package_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "package.json").write_text(
                '{"name":"Billing_Service","dependencies":{"Shared-Core":"^1.0.0"}}',
                encoding="utf-8",
            )
            identities, dependencies = repository_packages(directory)
        self.assertEqual(identities, {"billing-service"})
        self.assertEqual(dependencies, {"shared-core"})

    def test_reads_python_project_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "pyproject.toml").write_text(
                '[project]\nname="billing-api"\ndependencies=["shared_core>=1.2", "httpx"]\n',
                encoding="utf-8",
            )
            identities, dependencies = repository_packages(directory)
        self.assertEqual(identities, {"billing-api"})
        self.assertEqual(dependencies, {"shared-core", "httpx"})


if __name__ == "__main__":
    unittest.main()
