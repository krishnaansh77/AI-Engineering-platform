"""Dependency-free helpers for repository query caching."""
import hashlib
import re
from typing import Optional
import uuid


def build_query_cache_key(
    repo_id: uuid.UUID,
    last_indexed_at: Optional[str],
    question: str,
    top_k: int,
) -> str:
    """Build a stable key that changes whenever the indexed repository changes."""
    version = last_indexed_at or "unindexed"
    normalized_question = re.sub(r"\s+", " ", question).strip().lower()
    question_hash = hashlib.sha256(normalized_question.encode("utf-8")).hexdigest()
    return f"aise:query:{repo_id}:{version}:{top_k}:{question_hash}"
