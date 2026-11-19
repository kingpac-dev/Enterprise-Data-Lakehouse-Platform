import importlib.util
import io
import os
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("branch_audit", Path(__file__).resolve().parents[1] / "check_branch_isolation.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def fixture_fetch(principal, sql):
    if "serving.v_daily_branch_sales" in sql:
        return [{"branch_id": 1 if principal == "A" else 2}]
    raise audit.AccessDenied()


class BranchIsolationTests(unittest.TestCase):
    def test_separate_branches_and_explicit_base_denials_pass(self):
        audit.validate_isolation(fixture_fetch, 1, 2)

    def test_shared_visibility_fails(self):
        def fetch(principal, sql):
            if "serving.v_daily_branch_sales" in sql:
                return [{"branch_id": 1}, {"branch_id": 2}]
            raise audit.AccessDenied()
        with self.assertRaisesRegex(AssertionError, "branch isolation"):
            audit.validate_isolation(fetch, 1, 2)

    def test_successful_base_select_fails_even_if_empty(self):
        def fetch(principal, sql):
            if "mart.fact_sales" in sql:
                return []
            return fixture_fetch(principal, sql)
        with self.assertRaisesRegex(AssertionError, "base-table"):
            audit.validate_isolation(fetch, 1, 2)

    def test_connection_failure_is_not_treated_as_permission_denial(self):
        def fetch(principal, sql):
            if "serving.v_daily_branch_sales" in sql:
                return fixture_fetch(principal, sql)
            raise RuntimeError("unavailable")
        with self.assertRaisesRegex(RuntimeError, "unavailable"):
            audit.validate_isolation(fetch, 1, 2)

    def test_only_explicit_clickhouse_access_denied_is_accepted(self):
        def http_error(code):
            return urllib.error.HTTPError("http://example.invalid", 500, "error", {},
                                          io.BytesIO(f"Code: {code}. DB::Exception".encode()))
        with patch("urllib.request.urlopen", side_effect=http_error(497)), self.assertRaises(audit.AccessDenied):
            audit.query("http://example.invalid/", "user", "test", "SELECT 1")
        with patch("urllib.request.urlopen", side_effect=http_error(516)), \
                self.assertRaisesRegex(RuntimeError, "not an access-denied"):
            audit.query("http://example.invalid/", "user", "test", "SELECT 1")

    def test_endpoint_rejects_embedded_credentials(self):
        with patch.dict(os.environ, {"INSIGHT_TEST_CLICKHOUSE_URL": "https://user@example.invalid"}, clear=True), \
                self.assertRaises(ValueError):
            audit.endpoint_from_env()


if __name__ == "__main__":
    unittest.main()
