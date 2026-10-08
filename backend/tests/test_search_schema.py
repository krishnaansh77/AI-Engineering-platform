"""Tests for the semantic search response contract."""
import unittest

from app.api.schemas import SearchResponse, SearchResultSchema
from app.services.evaluation_service import aggregate_scores, score_retrieval


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

    def test_retrieval_metrics_calculate_recall_and_mrr(self):
        score = score_retrieval(["a.py", "b.py"], ["x.py", "b.py", "a.py"])
        self.assertEqual(score["recall"], 1.0)
        self.assertEqual(score["reciprocal_rank"], 0.5)
        self.assertEqual(aggregate_scores([score])["mrr"], 0.5)

    def test_aggregate_scores_includes_latency_when_available(self):
        result = aggregate_scores([
            {"recall": 1.0, "reciprocal_rank": 1.0, "retrieval_latency_ms": 20.0},
            {"recall": 0.0, "reciprocal_rank": 0.0, "retrieval_latency_ms": 40.0},
        ])
        self.assertEqual(result["average_retrieval_latency_ms"], 30.0)
        self.assertEqual(result["expected_file_hit_rate"], 0.5)

    def test_empty_aggregate_has_expected_file_hit_rate(self):
        self.assertEqual(aggregate_scores([])["expected_file_hit_rate"], 0.0)
