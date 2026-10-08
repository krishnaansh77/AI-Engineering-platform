"""Tests for the semantic search response contract."""
import unittest

from app.api.schemas import SearchResponse, SearchResultSchema


class TestSearchSchema(unittest.TestCase):
    def test_search_result_keeps_location_and_snippet(self):
        result = SearchResultSchema(
            file_path="backend/app/main.py",
            chunk_type="function",
            start_line=1,
            end_line=10,
            snippet="def main():",
            score=0.01,
        )
        response = SearchResponse(results=[result], query="startup")
        self.assertEqual(response.results[0].start_line, 1)
