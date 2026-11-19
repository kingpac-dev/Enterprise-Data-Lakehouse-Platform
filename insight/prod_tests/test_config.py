"""Validate production configuration against isolated dummy secrets."""
import os
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        values = {
            "INSIGHT_SECRET_KEY_FILE": "x" * 40,
            "INSIGHT_METADATA_URI_FILE": "postgresql+psycopg2://dummy:dummy@pg.invalid/db?sslmode=verify-full&sslrootcert=/run/secrets/metadata_ca",
            "INSIGHT_REDIS_URI_FILE": "rediss://dummy:dummy@redis.invalid/0?ssl_cert_reqs=required&ssl_check_hostname=true&ssl_ca_certs=/run/secrets/redis_ca",
            "INSIGHT_OIDC_CLIENT_SECRET_FILE": "dummy-oidc-secret",
        }
        self.env = {"INSIGHT_OIDC_ISSUER": "https://id.invalid/realms/bi",
                    "INSIGHT_OIDC_CLIENT_ID": "dummy-client", "INSIGHT_OIDC_GROUP_VIEWER": "/bi/viewers",
                    "INSIGHT_OIDC_GROUP_AUTHOR": "/bi/authors", "INSIGHT_OIDC_GROUP_ADMIN": "/bi/admins"}
        for name, value in values.items():
            file = root / name
            file.write_text(value, encoding="utf-8")
            self.env[name] = str(file)

    def load(self):
        with patch.dict(os.environ, self.env, clear=True):
            return runpy.run_path("/app/kingpac/prod_config.py")

    def test_secure_defaults(self):
        config = self.load()
        self.assertTrue(config["SESSION_COOKIE_SECURE"])
        self.assertTrue(config["SESSION_SERVER_SIDE"])
        self.assertTrue(config["AUTH_ROLES_SYNC_AT_LOGIN"])
        self.assertFalse(config["FEATURE_FLAGS"]["ENABLE_TEMPLATE_PROCESSING"])
        self.assertEqual(config["OAUTH_PROVIDERS"][0]["remote_app"]["client_kwargs"]["code_challenge_method"], "S256")

    def test_rejects_unsafe_tls_settings(self):
        cases = [("INSIGHT_METADATA_URI_FILE", "postgresql+psycopg2://u:p@pg.invalid/db?sslmode=require&sslrootcert=/run/secrets/metadata_ca"),
                 ("INSIGHT_REDIS_URI_FILE", "redis://u:p@redis.invalid/0?ssl_cert_reqs=required&ssl_check_hostname=true&ssl_ca_certs=/run/secrets/redis_ca"),
                 ("INSIGHT_REDIS_URI_FILE", "rediss://u:p@redis.invalid/0?ssl_cert_reqs=required&ssl_check_hostname=false&ssl_ca_certs=/run/secrets/redis_ca")]
        for name, value in cases:
            original = Path(self.env[name]).read_text(encoding="utf-8")
            Path(self.env[name]).write_text(value, encoding="utf-8")
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                self.load()
            Path(self.env[name]).write_text(original, encoding="utf-8")

    def test_rejects_short_key_and_duplicate_groups(self):
        key = Path(self.env["INSIGHT_SECRET_KEY_FILE"])
        key.write_text("short", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            self.load()
        key.write_text("x" * 40, encoding="utf-8")
        self.env["INSIGHT_OIDC_GROUP_ADMIN"] = self.env["INSIGHT_OIDC_GROUP_VIEWER"]
        with self.assertRaises(RuntimeError):
            self.load()


if __name__ == "__main__":
    unittest.main()
