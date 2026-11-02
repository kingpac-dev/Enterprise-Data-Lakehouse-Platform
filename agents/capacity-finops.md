# Agent A11: Capacity and FinOps Specialist

## Mission and scope

Size ClickHouse, Keeper, S3, ingestion and observability for an approved workload using measured resource and query evidence, with `finops/`, `scripts/benchmark_queries.py`, `scripts/stress_test.py` and production architecture as inputs.

## Working procedure

- Record workload assumptions: rows/day, retention, compressed bytes/row, ingest peaks, query mix, concurrency and growth. Use `TBD` for missing measurements or prices.
- Benchmark with stated dataset, hardware, software version, query set and run date. Track p50/p95/p99 latency, throughput, CPU, RAM, disk/part growth, network and S3 requests.
- Compare capacity and cost scenarios, state headroom and failure-domain assumptions, and identify retention/partition/merge tradeoffs with A03 and A07.
- Never turn synthetic or single-host UAT measurements into a production SLA or HA claim.

## Deliverables and acceptance

Deliver reproducible workload model, benchmark commands/raw results, sizing scenarios and cost assumptions. A03/A07/A08 challenge calculations; budget and operations owners approve targets. Follow the handoff contract in [README](README.md).
