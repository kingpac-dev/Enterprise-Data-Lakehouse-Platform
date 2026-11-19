"""Offline tests with synthetic claims; real Keycloak integration remains a gate."""
import unittest
from unittest.mock import patch

from flask import Flask
from prod_security import KingPacSecurityManager, map_userinfo
from superset.security import SupersetSecurityManager


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.claims = {"sub": "subject-1", "email": "user@example.invalid",
                       "email_verified": True, "groups": ["/bi/viewers"]}

    def test_identity_is_stable_and_issuer_scoped(self):
        a = map_userinfo(self.claims, {"sub": "subject-1"}, "https://id.example.invalid/realm")
        b = map_userinfo(self.claims, {"sub": "subject-1"}, "https://id.example.invalid/other")
        self.assertTrue(a["username"].startswith("kc_"))
        self.assertNotEqual(a["username"], b["username"])
        self.assertEqual(a["role_keys"], ["/bi/viewers"])

    def test_unverified_mismatched_or_invalid_claims_are_rejected(self):
        cases = [(self.claims, {"sub": "other"}),
                 ({**self.claims, "email_verified": False}, {"sub": "subject-1"}),
                 ({**self.claims, "groups": "viewers"}, {"sub": "subject-1"})]
        for userinfo, token in cases:
            with self.subTest(userinfo=userinfo, token=token), self.assertRaises(ValueError):
                map_userinfo(userinfo, token, "https://id.example.invalid/realm")
        with self.assertRaises(TypeError):
            map_userinfo(self.claims, None, "https://id.example.invalid/realm")

    def test_unmapped_group_cannot_authenticate(self):
        app = Flask(__name__)
        app.config["AUTH_ROLES_MAPPING"] = {"/bi/viewers": ["Gamma"]}
        manager = object.__new__(KingPacSecurityManager)
        with app.app_context(), patch.object(SupersetSecurityManager, "auth_user_oauth", return_value="allowed") as parent:
            self.assertIsNone(manager.auth_user_oauth({"role_keys": ["/other"]}))
            parent.assert_not_called()
            self.assertEqual(manager.auth_user_oauth({"role_keys": ["/bi/viewers"]}), "allowed")
            parent.assert_called_once()


if __name__ == "__main__":
    unittest.main()
