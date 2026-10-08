"""Tests for answer-level citation coverage heuristics."""
import asyncio
import uuid
import unittest

from app.providers.llm.base import LLMMessage, LLMProvider, LLMResponse
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievedChunk


class FixedProvider(LLMProvider):
    def __init__(self, answer: str):
        self.answer = answer

    def get_provider_name(self) -> str:
        return "fixed-test-provider"

    async def complete(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
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


if __name__ == "__main__":
    unittest.main()
