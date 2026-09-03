# ADR-0005: dbt-clickhouse for Medallion Data Transformation

## Status
Accepted

## Context
Data transformations from Raw to Silver (Core) and Gold (Mart) require version control, automated testing, documentation, and data lineage. Writing imperative ad-hoc SQL transformation scripts in disparate cron jobs creates technical debt and obscures dependencies.

## Decision
1. Standardize on **dbt (data build tool)** using the **`dbt-clickhouse`** adapter for declarative data modeling and transformations.
2. Structure dbt models into `bronze/` (source declarations and raw contracts), `silver/` (cleaned, deduplicated, conformed models), and `gold/` (dimensional star schemas and summary rollups).
3. Enforce automated dbt tests (uniqueness, non-null, referential integrity, and custom business rules) in the CI/CD pipeline before model promotion.

## Consequences
### Positive
- Declarative SQL with automatic DAG dependency resolution.
- Integrated testing and schema documentation generation.
- Clean Git-managed audit trail for all data transformations.

### Negative / Trade-offs
- Developers must learn dbt conventions and Jinja templating.
- Large table full refreshes must be managed carefully using ClickHouse incremental / partition-swapping strategies.
