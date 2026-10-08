"""Unit tests for Reciprocal Rank Fusion (RRF) algorithm and ranking logic."""
import unittest
import uuid
from types import SimpleNamespace

from app.services.retrieval_service import _metadata_ranked_ids


class TestRetrievalMath(unittest.TestCase):
    def test_metadata_ranking_prioritizes_named_service_files(self):
        target = uuid.uuid4()
        other = uuid.uuid4()
        chunks = [
            SimpleNamespace(id=other, file_path="backend/app/services/parser_service.py", symbol_name="parse", chunk_type="function"),
            SimpleNamespace(id=target, file_path="backend/app/services/secret_scan_service.py", symbol_name="scan", chunk_type="class"),
        ]
        ranked = _metadata_ranked_ids(chunks, "How are secret scan findings detected?", 2)
        self.assertEqual(ranked[0], target)

    def test_rrf_scoring_logic(self):
        """Verify that items ranked high in both vector and lexical search get higher RRF scores."""
        item_a = uuid.uuid4()
        item_b = uuid.uuid4()
        item_c = uuid.uuid4()

        vector_ranks = [item_a, item_b]  # item_a is rank 1, item_b is rank 2
        bm25_ranks = [item_a, item_c]    # item_a is rank 1, item_c is rank 2

        rrf_k = 60
        scores = {}

        for rank, cid in enumerate(vector_ranks, start=1):
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))

        for rank, cid in enumerate(bm25_ranks, start=1):
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))

        # item_a appears at rank 1 in both: 1/61 + 1/61 = 2/61 ≈ 0.03278
        # item_b appears only in vector at rank 2: 1/62 ≈ 0.01612
        # item_c appears only in bm25 at rank 2: 1/62 ≈ 0.01612
        self.assertGreater(scores[item_a], scores[item_b])
        self.assertGreater(scores[item_a], scores[item_c])
        self.assertAlmostEqual(scores[item_b], scores[item_c])

        sorted_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)
        self.assertEqual(sorted_ids[0], item_a)


if __name__ == "__main__":
    unittest.main()
