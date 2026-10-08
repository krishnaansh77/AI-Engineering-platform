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

    def test_classifies_repository_layers(self):
        self.assertEqual(DependencyGraphService.classify_layer("frontend/src/app/page.tsx"), "frontend")
        self.assertEqual(DependencyGraphService.classify_layer("backend/app/api/repos.py"), "backend")
        self.assertEqual(DependencyGraphService.classify_layer("backend/tests/test_graph.py"), "tests")

    def test_expands_dependents_from_changed_targets(self):
        edges = [
            {"source": "api.py", "target": "service.py"},
            {"source": "route.py", "target": "api.py"},
        ]
        impacted = DependencyGraphService.expand_dependents({"service.py"}, edges)
        self.assertEqual(impacted, {"api.py", "route.py"})


if __name__ == "__main__":
    unittest.main()
