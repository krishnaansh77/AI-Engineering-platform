"""Tests for deterministic query cache keys."""
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.query_cache import build_query_cache_key


class TestQueryCache(unittest.TestCase):
    def test_key_is_stable_for_case_and_whitespace(self):
        repo = SimpleNamespace(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            last_indexed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        first = build_query_cache_key(repo.id, repo.last_indexed_at.isoformat(), "  Where is auth? ", 5)
        second = build_query_cache_key(repo.id, repo.last_indexed_at.isoformat(), "where is auth?", 5)
        self.assertEqual(first, second)

    def test_reindex_version_changes_key(self):
        repo = SimpleNamespace(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            last_indexed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        first = build_query_cache_key(repo.id, repo.last_indexed_at.isoformat(), "Where is auth?", 5)
        repo.last_indexed_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
        self.assertNotEqual(first, build_query_cache_key(repo.id, repo.last_indexed_at.isoformat(), "Where is auth?", 5))
