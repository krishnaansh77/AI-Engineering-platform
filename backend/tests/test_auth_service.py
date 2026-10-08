"""Unit tests for Phase 4 password and token primitives."""
import uuid
import unittest
from app.services.auth_service import create_access_token, decode_access_token, hash_password, verify_password


class TestAuthService(unittest.TestCase):
    def test_password_hashing_is_salted_and_verifiable(self):
        first = hash_password("correct horse battery staple")
        second = hash_password("correct horse battery staple")
        self.assertNotEqual(first, second)
        self.assertTrue(verify_password("correct horse battery staple", first))
        self.assertFalse(verify_password("wrong password", first))

    def test_short_password_is_rejected(self):
        with self.assertRaises(ValueError):
            hash_password("short")

    def test_access_token_contains_identity_and_role(self):
        user_id = uuid.uuid4()
        claims = decode_access_token(create_access_token(user_id, "admin"))
        self.assertEqual(claims["sub"], str(user_id))
        self.assertEqual(claims["role"], "admin")


if __name__ == "__main__":
    unittest.main()
