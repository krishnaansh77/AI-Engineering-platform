"""Tests for the answer feedback contract."""
import unittest

from app.api.schemas import FeedbackRequest


class TestFeedbackSchema(unittest.TestCase):
    def test_accepts_supported_ratings(self):
        feedback = FeedbackRequest(
            question="Where is auth?",
            rating="helpful",
            model="gemini-3.8-flash",
            retrieval_count=5,
        )
        self.assertEqual(feedback.rating, "helpful")

    def test_rejects_unknown_rating(self):
        with self.assertRaises(ValueError):
            FeedbackRequest(question="Question", rating="maybe", model="model")
