"""Pure retrieval evaluation metrics used by the benchmark endpoint."""
from typing import Iterable, Sequence


def score_retrieval(expected_files: Iterable[str], retrieved_files: Sequence[str]) -> dict:
    """Calculate Recall@K and reciprocal rank for one retrieval case."""
    expected = {path for path in expected_files}
    if not expected:
        return {"recall": 0.0, "reciprocal_rank": 0.0, "matched_files": []}
    matched = [path for path in retrieved_files if path in expected]
    first_rank = next((index + 1 for index, path in enumerate(retrieved_files) if path in expected), None)
    return {
        "recall": round(len(set(matched)) / len(expected), 4),
        "reciprocal_rank": round(1 / first_rank, 4) if first_rank else 0.0,
        "matched_files": sorted(set(matched)),
    }


def aggregate_scores(scores: Sequence[dict]) -> dict:
    """Average per-case retrieval metrics."""
    if not scores:
        return {"recall_at_k": 0.0, "mrr": 0.0, "case_count": 0}
    return {
        "recall_at_k": round(sum(item["recall"] for item in scores) / len(scores), 4),
        "mrr": round(sum(item["reciprocal_rank"] for item in scores) / len(scores), 4),
        "case_count": len(scores),
    }
