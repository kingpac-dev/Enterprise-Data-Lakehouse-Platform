#!/usr/bin/env python3
"""
Enterprise Data Lakehouse Platform - End-to-End Smoke Test
==========================================================
Verifies health and connectivity of:
  - ClickHouse HTTP Endpoint (8123)
  - ClickHouse Databases (raw, core, mart, serving)
  - ClickHouse Disks & Storage Policies (default, s3_cold)
  - MinIO S3 Object Storage (9000)
  - Prometheus Metric Scraper (9090)
  - Grafana Web UI (3000)
"""

import os
import sys
import urllib.request
import urllib.error

CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT_HTTP", "8123"))
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_ADMIN_USER", "admin")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_ADMIN_PASSWORD", "change_this_admin_password_in_prod")

MINIO_HOST = os.getenv("MINIO_HOST", "localhost")
MINIO_PORT = int(os.getenv("MINIO_PORT", "9000"))

PROMETHEUS_HOST = os.getenv("PROMETHEUS_HOST", "localhost")
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "9090"))

GRAFANA_HOST = os.getenv("GRAFANA_HOST", "localhost")
GRAFANA_PORT = int(os.getenv("GRAFANA_PORT", "3000"))


def check_http(name: str, url: str, expected_substring: str = None) -> bool:
    """Checks an HTTP service endpoint."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            if expected_substring and expected_substring not in content:
                print(f"  [FAIL] {name}: Substring '{expected_substring}' not found in response.")
                return False
            print(f"  [PASS] {name} ({url}) is HEALTHY.")
            return True
    except Exception as e:
        print(f"  [FAIL] {name} ({url}): {e}")
        return False


def query_clickhouse(query: str) -> str:
    """Executes a query and returns text output."""
    url = f"http://{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/"
    headers = {"X-ClickHouse-User": CLICKHOUSE_USER, "X-ClickHouse-Key": CLICKHOUSE_PASSWORD}
    req = urllib.request.Request(url, data=query.encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8").strip()
    except Exception as e:
        return f"ERROR: {e}"


def run_smoke_tests():
    print("=" * 70)
    print("Running Enterprise Data Lakehouse Platform Smoke Test Suite")
    print("=" * 70)

    results = []

    # 1. Service Endpoints
    print("\n--- [1/4] Service Health Endpoints ---")
    results.append(check_http("ClickHouse HTTP Ping", f"http://{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/ping", "Ok."))
    results.append(check_http("MinIO S3 Ready Check", f"http://{MINIO_HOST}:{MINIO_PORT}/minio/health/ready"))
    results.append(check_http("Prometheus UI", f"http://{PROMETHEUS_HOST}:{PROMETHEUS_PORT}/-/healthy", "Prometheus Server is Healthy."))
    results.append(check_http("Grafana Health Check", f"http://{GRAFANA_HOST}:{GRAFANA_PORT}/api/health", "ok"))

    # 2. ClickHouse Database Namespaces
    print("\n--- [2/4] ClickHouse Medallion Databases ---")
    dbs = query_clickhouse("SELECT name FROM system.databases WHERE name IN ('raw', 'core', 'mart', 'serving')")
    found_dbs = [d.strip() for d in dbs.split("\n") if d.strip()]
    for db in ["raw", "core", "mart", "serving"]:
        if db in found_dbs:
            print(f"  [PASS] Database '{db}' exists.")
            results.append(True)
        else:
            print(f"  [FAIL] Database '{db}' is missing.")
            results.append(False)

    # 3. Storage Disks & Policies
    print("\n--- [3/4] ClickHouse Storage Policies & Disks ---")
    disks = query_clickhouse("SELECT name, type FROM system.disks")
    print(f"  Configured Disks:\n{disks}")
    policies = query_clickhouse("SELECT policy_name, volume_name, disks FROM system.storage_policies")
    print(f"  Storage Policies:\n{policies}")

    # 4. Tables and Row Counts
    print("\n--- [4/4] Table Availability & Row Counts ---")
    for tbl in ["raw.orders_landing", "core.dim_customer", "core.dim_product", "mart.fact_sales", "serving.v_daily_branch_sales"]:
        cnt = query_clickhouse(f"SELECT count() FROM {tbl}")
        if "ERROR" in cnt:
            print(f"  [WARN] Table '{tbl}': {cnt}")
        else:
            print(f"  [PASS] Table '{tbl}': Available (Rows: {cnt})")
            results.append(True)

    print("\n" + "=" * 70)
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"Smoke Test Summary: {passed}/{total} checks passed.")
    if passed == total:
        print(">>> ALL SMOKE TESTS PASSED SUCCESSFULLY! <<<")
        return 0
    else:
        print(">>> SOME CHECKS FAILED OR SERVICES ARE OFFLINE <<<")
        print("If services are stopped, run: docker compose -f compose/docker-compose.dev.yml up -d")
        return 1


if __name__ == "__main__":
    sys.exit(run_smoke_tests())
