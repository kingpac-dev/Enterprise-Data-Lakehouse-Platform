# Enterprise Data Lakehouse - FinOps & Workload Report

> **Report Generated:** 2026-09-04 04:50:57 UTC | **Cluster Engine:** ClickHouse 26.8 LTS | **Governance:** `AGENTS.md`

---

## 1. Executive Cost & Workload Summary

- **Total Queries Executed:** 20,011
- **Total Data Scanned (I/O):** 344.12 GB
- **Total Cumulative Duration:** 734.5 seconds
- **Estimated Compute & I/O Cost:** **$2.27 USD**

---

## 2. Cost Allocation by User Role & Workload

| User Role | Workload Kind | Query Count | Data Scanned (GB) | Peak RAM (MB) | Duration (sec) | Est. Cost (USD) | Cost Share |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `role_bi_readonly` | Select | 1,420 | 169.97 GB | 1764.3 MB | 312.4s | **$1.0798** | 47.6% |
| `role_api_service` | Select | 18,450 | 13.22 GB | 267.03 MB | 195.8s | **$0.2212** | 9.7% |
| `role_etl_service` | Insert | 96 | 49.17 GB | 3051.76 MB | 84.2s | **$0.3075** | 13.5% |
| `data_engineer` | Select | 45 | 111.76 GB | 4291.53 MB | 142.1s | **$0.6594** | 29.0% |

---

## 3. Workload Efficiency & Optimization Opportunities

| Role / Query Sample | Observation & Root Cause | Optimization Recommendation |
| :--- | :--- | :--- |
| `data_engineer`: `SELECT * FROM mart.fact_sales WHERE customer_id = 101` | High scan volume (120 GB) for single record lookup. Query did not specify `order_timestamp` or `branch_id`. | Add partition filter (`toYYYYMM(order_timestamp)`) or secondary index to prevent full table scan. |
| `role_bi_readonly`: Aggregating branch sales | Scans 182.5 GB over historical ranges. | Leverage pre-aggregated Materialized View `serving.mv_daily_sales_by_branch` for 95% I/O reduction. |
| `role_api_service`: High-frequency queries | Sub-second execution (<10ms) consuming minimal RAM. Highly optimal. | Retain current serving pattern with `LIMIT 100` guardrail. |

---

## 4. Quota Enforcement Rules (AGENTS.md Policy)

- **Maximum Query Execution Time**: 30 seconds for BI queries; 10 seconds for API queries.
- **Maximum Memory Usage**: 10 GB per user query (`max_memory_usage = 10000000000`).
- **Read-Only Enforcement**: Analytical roles (`role_bi_readonly`) are strictly prohibited from issuing DDL or DML statements.
