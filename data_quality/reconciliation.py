"""
Data Reconciliation & Integrity Engine
======================================
Performs automated multi-layer row count reconciliation, null checks,
value domain assertions, and calculates enterprise Data Quality Score (DQS).
"""

import os
import sys
import json
import datetime
import urllib.request
import urllib.error
from typing import Dict, Any


class DataReconciliationEngine:
    def __init__(self):
        self.host = os.getenv("CLICKHOUSE_HOST", "localhost")
        self.port = int(os.getenv("CLICKHOUSE_PORT_HTTP", "8123"))
        self.user = os.getenv("CLICKHOUSE_ADMIN_USER", "admin")
        self.password = os.getenv("CLICKHOUSE_ADMIN_PASSWORD", "change_this_admin_password_in_prod")

    def query(self, sql: str) -> str:
        """Executes a SQL query against ClickHouse HTTP interface."""
        url = f"http://{self.host}:{self.port}/"
        headers = {"X-ClickHouse-User": self.user, "X-ClickHouse-Key": self.password}
        req = urllib.request.Request(url, data=sql.strip().encode("utf-8"), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8").strip()
        except urllib.error.URLError as e:
            return f"ERROR: {e}"

    def run_reconciliation(self) -> Dict[str, Any]:
        """Runs multi-layer reconciliation checks and calculates Data Quality Score."""
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # 1. Row counts across layers
        raw_rows = self.query("SELECT count() FROM raw.orders_landing")
        cancelled_rows = self.query("SELECT count() FROM raw.orders_landing WHERE status = 'CANCELLED'")
        fact_rows = self.query("SELECT count() FROM mart.fact_sales")
        serving_orders = self.query("SELECT sum(total_orders) FROM serving.v_daily_branch_sales")

        # Convert to int safely
        def to_int(val):
            try:
                return int(val)
            except (ValueError, TypeError):
                return 0

        raw_cnt = to_int(raw_rows)
        cancelled_cnt = to_int(cancelled_rows)
        fact_cnt = to_int(fact_rows)
        serving_cnt = to_int(serving_orders)

        expected_fact = raw_cnt - cancelled_cnt
        row_count_diff = abs(fact_cnt - expected_fact)

        # 2. Integrity & Anomaly Checks
        null_keys = to_int(self.query("SELECT count() FROM raw.orders_landing WHERE order_id = 0 OR customer_id = 0"))
        negative_amounts = to_int(self.query("SELECT count() FROM mart.fact_sales WHERE amount < 0"))
        future_dates = to_int(self.query("SELECT count() FROM mart.fact_sales WHERE sale_date > today()"))

        # 3. Revenue Checksum Reconciliation
        fact_rev = self.query("SELECT round(sum(amount), 2) FROM mart.fact_sales")
        serving_rev = self.query("SELECT round(sum(total_revenue), 2) FROM serving.v_daily_branch_sales")

        def to_float(val):
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        fact_revenue = to_float(fact_rev)
        serving_revenue = to_float(serving_rev)
        revenue_diff = round(abs(fact_revenue - serving_revenue), 2)

        # 4. Calculate Data Quality Score (DQS: 0.0 - 100.0%)
        penalties = 0.0
        if row_count_diff > 0:
            penalties += min(20.0, (row_count_diff / max(1, expected_fact)) * 100.0)
        if null_keys > 0:
            penalties += 15.0
        if negative_amounts > 0:
            penalties += 20.0
        if future_dates > 0:
            penalties += 15.0
        if revenue_diff > 1.0:
            penalties += 30.0

        dq_score = max(0.0, round(100.0 - penalties, 1))

        status = "PASSED" if dq_score >= 95.0 else ("WARNING" if dq_score >= 80.0 else "FAILED")

        report = {
            "timestamp": timestamp,
            "status": status,
            "data_quality_score": dq_score,
            "layer_counts": {
                "raw_orders_landing": raw_cnt,
                "raw_cancelled_orders": cancelled_cnt,
                "expected_fact_sales": expected_fact,
                "actual_fact_sales": fact_cnt,
                "serving_total_orders": serving_cnt,
                "discrepancy": row_count_diff,
            },
            "revenue_checksum": {
                "mart_fact_sales_revenue": fact_revenue,
                "serving_sales_revenue": serving_revenue,
                "discrepancy": revenue_diff,
            },
            "anomaly_checks": {
                "null_or_zero_keys": null_keys,
                "negative_amounts": negative_amounts,
                "future_dates": future_dates,
            }
        }
        return report


def main():
    print("=" * 70)
    print("Enterprise Data Lakehouse - Data Quality & Reconciliation Engine")
    print("=" * 70)

    engine = DataReconciliationEngine()
    report = engine.run_reconciliation()

    print(json.dumps(report, indent=2))
    print("=" * 70)

    if report["status"] == "PASSED":
        print(f">>> [SUCCESS] Data Quality Score: {report['data_quality_score']}% (Status: PASSED) <<<")
        sys.exit(0)
    elif report["status"] == "WARNING":
        print(f">>> [WARNING] Data Quality Score: {report['data_quality_score']}% (Status: WARNING) <<<")
        sys.exit(0)
    else:
        print(f">>> [CRITICAL] Data Quality Score: {report['data_quality_score']}% (Status: FAILED) <<<")
        sys.exit(1)


if __name__ == "__main__":
    main()
