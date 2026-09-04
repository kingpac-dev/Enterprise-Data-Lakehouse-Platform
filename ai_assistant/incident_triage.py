#!/usr/bin/env python3
"""
=============================================================================
Enterprise Data Lakehouse Platform - AI Incident Triage Diagnostic (M09/M12)
=============================================================================
Automated diagnostic tool that analyzes ClickHouse errors, scrubs sensitive
credentials, matches error signatures to operational runbooks, and provides
concrete step-by-step remediation commands.

Adheres to AGENTS.md:
- Zero-Trust Log Scrubbing (scrubs IPs, passwords, tokens, customer data).
- Deterministic runbook action recommendations.
"""

import os
import re
import sys
import argparse
import logging
from typing import Dict, List, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [IncidentTriage] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("IncidentTriage")

# Known ClickHouse Incident Patterns & Runbook Mappings
INCIDENT_PATTERNS = [
    {
        "code": "TOO_MANY_PARTS",
        "regex": r"(Too many parts in all data parts|Code: 252|too many parts in table)",
        "title": "Active Parts Explosion (Micro-batching Saturation)",
        "severity": "CRITICAL",
        "runbook": "runbooks/03_troubleshooting_and_failover.md#parts-explosion",
        "root_cause": "Ingestion clients are inserting small micro-batches (< 1,000 rows) faster than ClickHouse background threads can merge data parts.",
        "remediation_steps": [
            "1. Client Optimization: Buffer writes into batches of >= 10,000 rows or every 2-5 seconds.",
            "2. Server-side Async Inserts: Enable settings: 'async_insert = 1, wait_for_async_insert = 1'.",
            "3. Emergency Remediation: Force immediate partition merge: 'OPTIMIZE TABLE <db>.<table> FINAL;'",
            "4. Verify active parts count: 'SELECT table, count() FROM system.parts WHERE active GROUP BY table;'"
        ]
    },
    {
        "code": "TABLE_IS_READ_ONLY",
        "regex": r"(Table is in readonly mode|Code: 242|Database is read-only|ZooKeeper session expired)",
        "title": "ClickHouse Keeper Raft Quorum Loss (Read-Only State)",
        "severity": "CRITICAL",
        "runbook": "runbooks/03_troubleshooting_and_failover.md#troubleshooting-clickhouse-keeper",
        "root_cause": "ClickHouse Server lost communication with ClickHouse Keeper or fewer than 2 of 3 Keeper quorum nodes are reachable.",
        "remediation_steps": [
            "1. Check Keeper container health: 'docker logs lakehouse-keeper-01'",
            "2. Verify Keeper Raft status: 'echo mntr | nc localhost 9181 | grep zk_server_state'",
            "3. Restart disconnected Keeper node to restore majority quorum (2 of 3 nodes).",
            "4. Once quorum is restored, ClickHouse tables will automatically release read-only state."
        ]
    },
    {
        "code": "MEMORY_LIMIT_EXCEEDED",
        "regex": r"(Memory limit .* exceeded|Code: 241|would use .* which is more than the limit)",
        "title": "Query Memory Quota Exceeded (RAM Limit Breach)",
        "severity": "HIGH",
        "runbook": "runbooks/03_troubleshooting_and_failover.md#query-errors",
        "root_cause": "An analytical query attempted to allocate more memory than permitted by the user profile quota ('max_memory_usage').",
        "remediation_steps": [
            "1. Add partition pruning filter: ensure query specifies 'toYYYYMM(event_timestamp)'.",
            "2. Use pre-aggregated Materialized View: redirect query from 'mart.fact_sales' to 'serving.mv_daily_sales_by_branch'.",
            "3. Check current memory consumers: 'SELECT query_id, user, memory_usage, query FROM system.processes ORDER BY memory_usage DESC;'",
            "4. Terminate runaway query if needed: 'KILL QUERY WHERE query_id = '<id>';'"
        ]
    },
    {
        "code": "REPLICATION_LAG",
        "regex": r"(Replication queue lag|ReplicationQueueLag|is lagging behind leader)",
        "title": "Data Replication Lag between Cluster Nodes",
        "severity": "HIGH",
        "runbook": "runbooks/03_troubleshooting_and_failover.md#replication-lag",
        "root_cause": "Target replica is processing mutations or downloading parts slower than the active leader node.",
        "remediation_steps": [
            "1. Inspect replication queue: 'SELECT table, count() FROM system.replication_queue GROUP BY table;'",
            "2. Check intra-cluster network connectivity between Node 1 and Node 2 on port 9009.",
            "3. Check disk I/O utilization on lagging host: 'iostat -xz 1 5'."
        ]
    }
]


def scrub_sensitive_data(raw_log: str) -> str:
    """
    Zero-Trust Log Sanitizer:
    Removes IP addresses, tokens, passwords, and sensitive credentials.
    """
    # Scrub IPv4 addresses
    scrubbed = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "[REDACTED_IP]", raw_log)
    # Scrub password values
    scrubbed = re.sub(r"(password|secret|token|key)[:=][\s]*[^\s,;&]+", r"\1=[REDACTED]", scrubbed, flags=re.IGNORECASE)
    # Scrub email addresses
    scrubbed = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b", "[REDACTED_EMAIL]", scrubbed)
    return scrubbed


def triage_log(log_content: str) -> List[Dict[str, Any]]:
    """Analyzes log string and matches recognized incident patterns."""
    sanitized_log = scrub_sensitive_data(log_content)
    diagnoses = []

    for pattern in INCIDENT_PATTERNS:
        match = re.search(pattern["regex"], sanitized_log, re.IGNORECASE)
        if match:
            diagnoses.append({
                "code": pattern["code"],
                "title": pattern["title"],
                "severity": pattern["severity"],
                "matched_text": match.group(0),
                "runbook": pattern["runbook"],
                "root_cause": pattern["root_cause"],
                "remediation_steps": pattern["remediation_steps"]
            })

    return diagnoses


def main():
    parser = argparse.ArgumentParser(description="ClickHouse AI Incident Triage Diagnostic (M09/M12)")
    parser.add_argument("--simulate", choices=["TOO_MANY_PARTS", "TABLE_IS_READ_ONLY", "MEMORY_LIMIT_EXCEEDED", "REPLICATION_LAG"],
                        help="Simulate diagnosis of a specific ClickHouse incident")
    parser.add_argument("--log-file", help="Path to log file to triage")

    args = parser.parse_args()

    print("=" * 68)
    print(" ENTERPRISE CLICKHOUSE AI INCIDENT TRIAGE DIAGNOSTIC (M09/M12)")
    print("=" * 68)

    sample_logs = {
        "TOO_MANY_PARTS": "DB::Exception: Code: 252. DB::Exception: Too many parts in all data parts in table raw.orders_landing (312 parts). Merges are processing slower than inserts. Password=supersecret IP: 192.168.1.100",
        "TABLE_IS_READ_ONLY": "DB::Exception: Code: 242. Table is in readonly mode: ZooKeeper session expired, Raft quorum lost on keeper node 10.0.0.5 with token=xyz123",
        "MEMORY_LIMIT_EXCEEDED": "DB::Exception: Code: 241. Memory limit (for query) exceeded: would use 11.20 GiB (limit: 10.00 GiB). Query from user admin@enterprise.com",
        "REPLICATION_LAG": "Warning: ReplicationQueueLag exceeded 150 tasks on table mart.fact_sales replica 172.20.0.12"
    }

    log_to_process = ""
    if args.simulate:
        log_to_process = sample_logs[args.simulate]
        print(f" Simulating Incident: [{args.simulate}]")
    elif args.log_file and os.path.exists(args.log_file):
        with open(args.log_file, "r", encoding="utf-8") as f:
            log_to_process = f.read()
    else:
        # Default simulation
        log_to_process = sample_logs["TOO_MANY_PARTS"]
        print(" Defaulting to demonstration incident: [TOO_MANY_PARTS]")

    sanitized = scrub_sensitive_data(log_to_process)
    print("-" * 68)
    print(f" Sanitized Input Log (Zero-Trust Scrubbed):")
    print(f" \"{sanitized}\"")
    print("-" * 68)

    diagnoses = triage_log(log_to_process)

    if not diagnoses:
        print("\n[RESULT] No known incident signatures identified in log.")
    else:
        for idx, d in enumerate(diagnoses, start=1):
            print(f"\nINCIDENT DIAGNOSIS #{idx}: [{d['severity']}] {d['title']}")
            print(f"  Incident Code : {d['code']}")
            print(f"  Root Cause    : {d['root_cause']}")
            print(f"  Action Runbook: {d['runbook']}")
            print("  Remediation Actions:")
            for step in d["remediation_steps"]:
                print(f"    {step}")

    print("\n" + "=" * 68)
    print(" INCIDENT TRIAGE SUMMARY: RESOLUTION RUNBOOK ATTACHED")
    print("=" * 68 + "\n")


if __name__ == "__main__":
    main()
