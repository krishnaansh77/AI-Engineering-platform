"""Tests for repository-local import resolution."""
import unittest

from app.services.graph_service import DependencyGraphService


class TestDependencyGraphService(unittest.TestCase):
    def test_resolves_python_package_under_backend_root(self):
        known = {"backend/app/config.py"}
        resolved = DependencyGraphService.resolve_import(
            "backend/app/main.py", "from app.config import settings", known
        )
        self.assertEqual(resolved, "backend/app/config.py")

    def test_resolves_relative_typescript_import(self):
        known = {"frontend/src/lib/api.ts"}
        resolved = DependencyGraphService.resolve_import(
            "frontend/src/app/page.tsx", 'import { api } from "../lib/api"', known
        )
        self.assertEqual(resolved, "frontend/src/lib/api.ts")


if __name__ == "__main__":
    unittest.main()
