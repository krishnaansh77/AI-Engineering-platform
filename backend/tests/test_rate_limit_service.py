"""Tests for endpoint-specific request throttling classification."""
import unittest

from app.services.rate_limit_service import rate_limit_for_path


class TestRateLimitService(unittest.TestCase):
    def test_expensive_query_uses_expensive_bucket(self):
        self.assertEqual(rate_limit_for_path("/repos/abc/query", 120, 30), (30, "expensive"))

    def test_expensive_nested_route_uses_expensive_bucket(self):
        self.assertEqual(rate_limit_for_path("/repos/abc/issues/12/analysis", 120, 30), (30, "expensive"))

    def test_read_only_route_uses_default_bucket(self):
        self.assertEqual(rate_limit_for_path("/repos/abc/history", 120, 30), (120, "default"))

    def test_auth_route_uses_auth_bucket_when_configured(self):
        self.assertEqual(rate_limit_for_path("/auth/login", 120, 30, 10), (10, "auth"))
