"""Tests for bounded repository-agent planning and tool isolation."""
import unittest

from app.services.agent_service import RepositoryAgent, run_optional_tool


class TestRepositoryAgent(unittest.TestCase):
    def test_plans_only_tools_relevant_to_question(self):
        self.assertEqual(RepositoryAgent.plan_tools("Where is login implemented?"), ["search_code"])
        self.assertEqual(
            RepositoryAgent.plan_tools("What changed recently and what tests cover it?"),
            ["search_code", "get_history", "get_tests"],
        )

    def test_plans_source_read_for_explicit_path(self):
        self.assertIn("get_file", RepositoryAgent.plan_tools("Explain backend/app/main.py"))


class TestOptionalAgentTool(unittest.IsolatedAsyncioTestCase):
    async def test_tool_failure_becomes_evidence_instead_of_aborting(self):
        def unavailable():
            raise RuntimeError("clone unavailable")

        result = await run_optional_tool("get_history", unavailable)
        self.assertEqual(result["tool"], "get_history")
        self.assertIn("error", result)

    async def test_successful_async_tool_result_is_named(self):
        async def tool():
            return {"count": 3}

        self.assertEqual(await run_optional_tool("get_tests", tool), {"tool": "get_tests", "count": 3})


if __name__ == "__main__":
    unittest.main()
