import unittest

from app.services.usage_service import estimate_llm_cost


class TestUsageService(unittest.TestCase):
    def test_estimates_cost_from_configured_rates(self):
        self.assertEqual(estimate_llm_cost(500_000, 250_000, 2.0, 4.0), 2.0)

    def test_negative_inputs_and_rates_are_clamped(self):
        self.assertEqual(estimate_llm_cost(-1, 100, -2.0, 3.0), 0.0003)
