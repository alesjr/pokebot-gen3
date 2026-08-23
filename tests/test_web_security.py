import unittest
from types import SimpleNamespace
from unittest.mock import patch
from aiohttp import web
from argon2 import PasswordHasher
from modules.web.security import DashboardSecurity

class TestDashboardSecurity(unittest.TestCase):
    def setUp(self):
        self.security = DashboardSecurity(
            "ash",
            PasswordHasher().hash("correct horse battery staple"),
            "shared-test-secret-with-at-least-32-characters",
        )

    def test_valid_login_creates_session(self):
        authenticated = self.security.authenticate("ash", "correct horse battery staple", "127.0.0.1")
        self.assertIsNotNone(authenticated)
        token, session = authenticated
        self.assertGreater(len(token), 64)
        self.assertGreater(len(session.csrf_token), 32)

    def test_wrong_credentials_do_not_create_session(self):
        self.assertIsNone(self.security.authenticate("ash", "wrong", "127.0.0.1"))

    def test_signed_session_is_accepted_by_another_process(self):
        token, original = self.security.authenticate("ash", "correct horse battery staple", "127.0.0.1")
        other_process = DashboardSecurity(
            "ash",
            self.security.password_hash,
            "shared-test-secret-with-at-least-32-characters",
        )
        restored = other_process.session(SimpleNamespace(cookies={"pokebot_session": token}))
        self.assertEqual(restored.csrf_token, original.csrf_token)

    def test_login_rate_limit(self):
        with patch("modules.web.security.LOGIN_ATTEMPTS", 1):
            self.assertIsNone(self.security.authenticate("ash", "wrong", "203.0.113.1"))
            with self.assertRaises(web.HTTPTooManyRequests):
                self.security.authenticate("ash", "wrong", "203.0.113.1")

if __name__ == "__main__":
    unittest.main()
