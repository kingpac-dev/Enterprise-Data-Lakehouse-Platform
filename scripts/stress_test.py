#!/usr/bin/env python3
"""
=============================================================================
Enterprise Data Lakehouse Platform - Concurrency Stress Test & Benchmark (M09)
=============================================================================
Simulates concurrent analytical users and BI dashboard workloads against
ClickHouse serving and mart layers.

Features:
- Multi-threaded query generation (5 - 50 concurrent workers).
- Latency percentiles calculation (P50, P90, P95, P99).
- Throughput (QPS) and error rate tracking.
- Built-in dry-run simulation mode when cluster is offline.
- Formatted SLA Scorecard report.
"""

import os
import sys
import time
import math
import random
import urllib.request
import urllib.parse
import argparse
import threading
from typing import List, Dict, Any

BENCHMARK_QUERIES = [
    {
        "name": "Daily Branch Aggregates",
        "sql": "SELECT sales_date, branch_id, sum(total_revenue) AS rev FROM serving.v_daily_branch_sales GROUP BY sales_date, branch_id ORDER BY sales_date DESC LIMIT 50 FORMAT JSON",
        "target_p95_ms": 150.0
    },
    {
        "name": "Product Performance Ranking",
        "sql": "SELECT product_id, count() AS total_orders, sum(net_amount) AS revenue FROM mart.fact_sales GROUP BY product_id ORDER BY revenue DESC LIMIT 20 FORMAT JSON",
        "target_p95_ms": 250.0
    },
    {
        "name": "Customer Segment Analysis",
        "sql": "SELECT c.customer_segment, count() AS orders, avg(f.net_amount) AS aov FROM core.dim_customer c JOIN mart.fact_sales f ON c.customer_id = f.customer_id GROUP BY c.customer_segment FORMAT JSON",
        "target_p95_ms": 350.0
    },
    {
        "name": "Serving Materialized View Check",
        "sql": "SELECT branch_id, finalizeAggregation(total_revenue) FROM serving.mv_daily_sales_by_branch GROUP BY branch_id LIMIT 10 FORMAT JSON",
        "target_p95_ms": 100.0
    }
]


class ConcurrencyStressTester:
    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        concurrency: int,
        requests_per_worker: int,
        dry_run: bool
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.concurrency = concurrency
        self.requests_per_worker = requests_per_worker
        self.dry_run = dry_run
        self.base_url = f"http://{self.host}:{self.port}/"
        self.latencies_ms: List[float] = []
        self.errors = 0
        self.lock = threading.Lock()

    def _execute_query(self, query: str) -> float:
        """Executes query and returns latency in milliseconds."""
        if self.dry_run:
            # Simulate realistic ClickHouse sub-second execution latency
            simulated_latency = random.uniform(8.0, 45.0) + (random.uniform(0.0, 10.0) if random.random() > 0.8 else 0.0)
            time.sleep(simulated_latency / 1000.0)
            return simulated_latency

        params = urllib.parse.urlencode({
            "user": self.user,
            "password": self.password,
            "query": query
        })
        url = f"{self.base_url}?{params}"
        req = urllib.request.Request(url)

        start = time.time()
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
            return (time.time() - start) * 1000.0
        except Exception:
            return -1.0

    def _worker(self, worker_id: int):
        for _ in range(self.requests_per_worker):
            q_info = random.choice(BENCHMARK_QUERIES)
            latency = self._execute_query(q_info["sql"])
            with self.lock:
                if latency >= 0:
                    self.latencies_ms.append(latency)
                else:
                    self.errors += 1

    def run(self) -> Dict[str, Any]:
        total_planned_requests = self.concurrency * self.requests_per_worker
        print("=" * 65)
        print(" ENTERPRISE CLICKHOUSE CONCURRENCY STRESS TEST (M09)")
        print("=" * 65)
        print(f" Target Endpoint     : {self.base_url}")
        print(f" Concurrency Level   : {self.concurrency} concurrent worker threads")
        print(f" Requests per Worker : {self.requests_per_worker}")
        print(f" Total Requests      : {total_planned_requests}")
        print(f" Execution Mode      : {'Simulated (Dry Run)' if self.dry_run else 'Live ClickHouse Cluster'}")
        print("-" * 65)

        start_time = time.time()
        threads = []
        for i in range(self.concurrency):
            t = threading.Thread(target=self._worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        total_wall_time = time.time() - start_time
        successful_requests = len(self.latencies_ms)
        qps = round(successful_requests / max(total_wall_time, 0.001), 2)
        error_rate = round((self.errors / max(total_planned_requests, 1)) * 100, 2)

        sorted_latencies = sorted(self.latencies_ms) if self.latencies_ms else [0.0]

        def get_percentile(p: float) -> float:
            if not sorted_latencies:
                return 0.0
            idx = int(math.ceil(p * len(sorted_latencies))) - 1
            return round(sorted_latencies[max(0, min(idx, len(sorted_latencies) - 1))], 2)

        min_ms = round(min(sorted_latencies), 2) if sorted_latencies else 0.0
        avg_ms = round(sum(sorted_latencies) / max(len(sorted_latencies), 1), 2)
        p50_ms = get_percentile(0.50)
        p90_ms = get_percentile(0.90)
        p95_ms = get_percentile(0.95)
        p99_ms = get_percentile(0.99)
        max_ms = round(max(sorted_latencies), 2) if sorted_latencies else 0.0

        sla_pass = (p95_ms <= 300.0) and (error_rate == 0.0)

        print("\n" + "=" * 65)
        print(" CONCURRENCY BENCHMARK RESULTS & SLA EVALUATION")
        print("=" * 65)
        print(f" Total Completed Req : {successful_requests} / {total_planned_requests}")
        print(f" Failed Requests     : {self.errors} (Error Rate: {error_rate}%)")
        print(f" Total Wall Time     : {round(total_wall_time, 2)}s")
        print(f" Throughput          : {qps} Queries/Sec (QPS)")
        print("-" * 65)
        print(" LATENCY DISTRIBUTION (ms):")
        print(f"   Min Latency       : {min_ms} ms")
        print(f"   Average Latency   : {avg_ms} ms")
        print(f"   Median (P50)      : {p50_ms} ms")
        print(f"   P90 Latency       : {p90_ms} ms")
        print(f"   P95 Latency       : {p95_ms} ms  [Target: <= 300 ms]")
        print(f"   P99 Latency       : {p99_ms} ms")
        print(f"   Max Latency       : {max_ms} ms")
        print("-" * 65)
        print(f" SLA Evaluation      : {'PASSED (Within Production SLA)' if sla_pass else 'FAILED (SLA Breached)'}")
        print("=" * 65 + "\n")

        return {
            "total_requests": total_planned_requests,
            "successful_requests": successful_requests,
            "errors": self.errors,
            "error_rate_pct": error_rate,
            "duration_sec": round(total_wall_time, 2),
            "qps": qps,
            "p50_ms": p50_ms,
            "p90_ms": p90_ms,
            "p95_ms": p95_ms,
            "p99_ms": p99_ms,
            "sla_pass": sla_pass
        }


def main():
    parser = argparse.ArgumentParser(description="ClickHouse Analytical Concurrency Stress Test (M09)")
    parser.add_argument("--host", default=os.environ.get("CLICKHOUSE_HOST", "localhost"), help="ClickHouse host")
    parser.add_argument("--port", type=int, default=int(os.environ.get("CLICKHOUSE_HTTP_PORT", 8123)), help="ClickHouse HTTP port")
    parser.add_argument("--user", default=os.environ.get("CLICKHOUSE_USER", "default"), help="ClickHouse user")
    parser.add_argument("--password", default=os.environ.get("CLICKHOUSE_PASSWORD", ""), help="ClickHouse password")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent worker threads (default: 10)")
    parser.add_argument("--requests", type=int, default=10, help="Requests per worker thread (default: 10)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate multi-threaded stress test without cluster connection")

    args = parser.parse_args()
    tester = ConcurrencyStressTester(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        concurrency=args.concurrency,
        requests_per_worker=args.requests,
        dry_run=args.dry_run
    )
    results = tester.run()
    if not results["sla_pass"] and not args.dry_run:
        sys.exit(1)


if __name__ == "__main__":
    main()
