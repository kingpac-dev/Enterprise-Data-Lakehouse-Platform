"""Read-only UAT audit of two ClickHouse branch-scoped service accounts.

Credentials and endpoint are provided through environment variables. This probes
the actual serving path; it does not configure permissions or prove UI/SQL Lab
authorization. Use only a synthetic UAT fixture containing both branches.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit


class AccessDenied(Exception):
    """ClickHouse explicitly rejected SELECT because privileges were missing."""


def required(name):
    value = os.environ.get(name, "")
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def endpoint_from_env():
    endpoint = required("INSIGHT_TEST_CLICKHOUSE_URL")
    try:
        parts = urlsplit(endpoint)
        _ = parts.port
    except ValueError as exc:
        raise ValueError("Invalid ClickHouse endpoint") from exc
    if (parts.scheme not in ("http", "https") or not parts.hostname
            or parts.username is not None or parts.password is not None
            or parts.path not in ("", "/") or parts.query or parts.fragment
            or any(char.isspace() for char in endpoint)):
        raise ValueError("Use an HTTP(S) endpoint without credentials, path, query or fragment")
    return endpoint.rstrip("/") + "/"


def query(endpoint, username, password, sql):
    request = urllib.request.Request(
        endpoint,
        data=(sql + " FORMAT JSON").encode("utf-8"),
        headers={"X-ClickHouse-User": username, "X-ClickHouse-Key": password},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response).get("data", [])
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(16384).decode("utf-8", errors="replace")
        finally:
            exc.close()
        if re.search(r"\bCode:\s*497\b", body, flags=re.IGNORECASE):
            raise AccessDenied() from None
        # Avoid logging credentials, query content, or database error details.
        raise RuntimeError(f"ClickHouse returned HTTP {exc.code}; this is not an access-denied result") from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
        raise RuntimeError("ClickHouse connection or response failed") from None


def validate_isolation(fetch, branch_a, branch_b):
    """Fail unless both principals see only their fixture branch and no base tables."""
    if not (0 <= branch_a <= 4294967295 and 0 <= branch_b <= 4294967295) or branch_a == branch_b:
        raise ValueError("Use two different UAT branch IDs in the UInt32 range")
    for principal, expected in (("A", branch_a), ("B", branch_b)):
        rows = fetch(principal, "SELECT DISTINCT branch_id FROM serving.v_daily_branch_sales ORDER BY branch_id LIMIT 1001")
        if len(rows) >= 1001 or {int(row["branch_id"]) for row in rows} != {expected}:
            raise AssertionError(f"Principal {principal}: fixture branch isolation failed or fixture is missing")
        for table in ("raw.orders_landing", "core.dim_customer", "mart.fact_sales"):
            try:
                fetch(principal, f"SELECT 1 FROM {table} LIMIT 1")
            except AccessDenied:
                continue
            raise AssertionError(f"Principal {principal}: direct base-table access was not denied")


def main():
    endpoint = endpoint_from_env()
    users = {label: (required(f"INSIGHT_TEST_BRANCH_{label}_USER"),
                     required(f"INSIGHT_TEST_BRANCH_{label}_PASSWORD")) for label in ("A", "B")}
    if users["A"][0] == users["B"][0]:
        raise ValueError("Use separate ClickHouse accounts for the two branches")
    branch_a = int(required("INSIGHT_TEST_BRANCH_A_ID"))
    branch_b = int(required("INSIGHT_TEST_BRANCH_B_ID"))

    def fetch(principal, sql):
        username, password = users[principal]
        return query(endpoint, username, password, sql)

    validate_isolation(fetch, branch_a, branch_b)
    print("PASS: two UAT accounts see only their fixture branch and cannot SELECT the tested base tables.")
    print("UI, export, SQL Lab, cache isolation, writes and other objects require separate tests.")


if __name__ == "__main__":
    try:
        main()
    except AccessDenied:
        print("FAIL: account cannot SELECT the test serving view.", file=sys.stderr)
        raise SystemExit(1) from None
    except (AssertionError, ValueError, RuntimeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1) from None
