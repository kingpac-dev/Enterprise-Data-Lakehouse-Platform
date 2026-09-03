# ADR-0002: ClickHouse Medallion Architecture and Database Layering

## Status
Accepted

## Context
Raw data arriving from heterogeneous enterprise sources (SQL Server, PostgreSQL, APIs, ERP, flat files) varies significantly in cleanliness, consistency, and schema stability. Analytical consumers (Power BI, dashboard APIs, data analysts) require reliable, consistent, and fast data without being exposed to raw pipeline artifacts or unhandled CDC tombstones.

## Decision
Organize the ClickHouse data warehouse into four distinct logical database namespaces:
1. `raw`: Ingestion landing layer. Append-only, source-aligned schemas with mandatory technical metadata columns (`_source_system`, `_source_table`, `_ingested_at`, `_source_updated_at`, `_batch_id`, `_record_hash`, `_is_deleted`).
2. `core`: Cleansed, normalized, deduplicated, and conformed silver layer. Uses `ReplacingMergeTree` for change data capture (CDC) deduplication.
3. `mart`: Business dimensional models (star schemas, conformed dimensions, fact tables) and summary aggregates for analytical domain consumption.
4. `serving`: High-speed consumption layer consisting of views, Materialized Views, and pre-computed caches optimized specifically for BI dashboards and application APIs.

## Consequences
### Positive
- Clear separation of concerns, data lineage, and auditability.
- Strict data contract boundaries between ingestion, engineering, and business consumers.
- Simplified access control (BI tools only need read grants to `mart` and `serving`).

### Negative / Trade-offs
- Additional storage footprint for intermediate layers (mitigated by TTL policies on raw data).
- Requires transformation orchestration (handled via `dbt-clickhouse`).
