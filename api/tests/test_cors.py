"""Exercise browser preflight behavior without a running ClickHouse server."""

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))


def app_for(settings):
    with patch.dict(os.environ, settings, clear=True):
        spec = importlib.util.spec_from_file_location("insight_api_cors_test", API_ROOT / "main.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module.app


class CORSTests(unittest.TestCase):
    def test_default_does_not_allow_cross_origin_requests(self):
        with TestClient(app_for({})) as client:
            response = client.get("/health", headers={"Origin": "https://unknown.example"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("access-control-allow-origin", response.headers)

    def test_explicit_origin_allows_get_but_not_other_origins_or_methods(self):
        settings = {"API_CORS_ALLOWED_ORIGINS": "https://bi.example, https://other.example"}
        with TestClient(app_for(settings)) as client:
            allowed = client.options("/health", headers={"Origin": "https://bi.example",
                "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "authorization"})
            denied_origin = client.options("/health", headers={"Origin": "https://unknown.example",
                "Access-Control-Request-Method": "GET"})
            denied_method = client.options("/health", headers={"Origin": "https://bi.example",
                "Access-Control-Request-Method": "POST"})
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.headers["access-control-allow-origin"], "https://bi.example")
        self.assertNotIn("access-control-allow-credentials", allowed.headers)
        self.assertEqual(denied_origin.status_code, 400)
        self.assertEqual(denied_method.status_code, 400)

    def test_credentials_require_explicit_opt_in(self):
        settings = {"API_CORS_ALLOWED_ORIGINS": "https://bi.example", "API_CORS_ALLOW_CREDENTIALS": "true"}
        with TestClient(app_for(settings)) as client:
            response = client.get("/health", headers={"Origin": "https://bi.example"})
        self.assertEqual(response.headers["access-control-allow-credentials"], "true")

    def test_invalid_origins_and_boolean_fail_on_startup(self):
        for invalid in ["*", "null", "https://example.com/path", "https://user@example.com", "https://*.example.com"]:
            with self.subTest(origin=invalid), self.assertRaises(ValueError):
                app_for({"API_CORS_ALLOWED_ORIGINS": invalid})
        with self.assertRaises(ValueError):
            app_for({"API_CORS_ALLOW_CREDENTIALS": "yes"})


if __name__ == "__main__":
    unittest.main()
