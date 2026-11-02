"""Tests for answer-level citation coverage heuristics."""
import asyncio
import uuid
import unittest
from unittest.mock import patch

from app.providers.llm.base import LLMMessage, LLMProvider, LLMResponse
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievedChunk


class FixedProvider(LLMProvider):
    def __init__(self, answer: str):
        self.answer = answer
        self.messages = []
        self.complete_kwargs = {}

    def get_provider_name(self) -> str:
        return "fixed-test-provider"

    async def complete(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        self.messages = messages
        self.complete_kwargs = kwargs
        return LLMResponse(self.answer, "fixed", 1, 1)


def chunk(file_path: str, symbol: str | None) -> RetrievedChunk:
    return RetrievedChunk(uuid.uuid4(), file_path, symbol, "function", 1, 4, "code", "python", 1.0)


class TestCitationCoverage(unittest.TestCase):
    def test_counts_only_citations_referenced_by_answer(self):
        service = LLMService(FixedProvider("The login flow is implemented in `src/auth.py`."))
        result = asyncio.run(service.answer_query(
            "Where is login?",
            [chunk("src/auth.py", "login"), chunk("src/db.py", "connect")],
            "acme/demo",
        ))
        self.assertEqual(result.citation_coverage, 0.5)

    def test_empty_citations_have_zero_coverage(self):
        service = LLMService(FixedProvider("No matching code was found."))
        result = asyncio.run(service.answer_query("Unknown", [], "acme/demo"))
        self.assertEqual(result.citation_coverage, 0.0)

    def test_context_budget_bounds_prompt_and_citations(self):
        provider = FixedProvider("See src/file_0.py")
        service = LLMService(provider)
        chunks = [
            RetrievedChunk(
                uuid.uuid4(), f"src/file_{index}.py", None, "function", 1, 400,
                "x" * 4500, "python", 1.0 - index / 100,
            )
            for index in range(8)
        ]

        result = asyncio.run(service.answer_query("Explain the code", chunks, "acme/demo"))

        user_prompt = provider.messages[1].content
        context_prompt = user_prompt.split("\n\nRepository:", 1)[1].split(
            "\n\nPlease provide", 1
        )[0]
        self.assertLessEqual(len(context_prompt), 18000)
        self.assertLess(len(result.citations), len(chunks))
        included_paths = [citation.file_path for citation in result.citations]
        self.assertEqual(included_paths, [f"src/file_{index}.py" for index in range(4)])

    def test_simple_query_uses_configured_model_only_when_enabled(self):
        provider = FixedProvider("The login handler is in src/auth.py")
        with (
            patch("app.services.llm_service.get_llm_provider", return_value=provider) as factory,
            patch("app.services.llm_service.settings.LLM_PROVIDER", "openai"),
            patch("app.services.llm_service.settings.LLM_SIMPLE_MODEL", "gpt-4o-mini"),
        ):
            service = LLMService()
            asyncio.run(service.answer_query("Where is login?", [chunk("src/auth.py", "login")], "acme/demo"))

        factory.assert_any_call(model_name="gpt-4o-mini")
        self.assertEqual(provider.complete_kwargs["max_tokens"], 512)

    def test_synthesis_questions_are_not_classified_as_simple(self):
        self.assertFalse(LLMService._is_simple_query("Why does login fail across services?"))
        self.assertFalse(LLMService._is_simple_query("Compare the authentication architectures"))
        self.assertTrue(LLMService._is_simple_query("Where is login handled?"))


if __name__ == "__main__":
    unittest.main()
