# Enterprise Data Lakehouse Platform - System Design & Generation Plan

This implementation plan translates all architectural specifications from `/docs` (DOC-01 through DOC-07, and the ClickHouse/Portainer blueprint) and the **AI System Design & Generation Prompt Template** into a fully realized, production-ready codebase for immediate deployment, validation, and real-world enterprise operations.

## Architecture & Governance Baseline

- **Platform Runtime**: Ubuntu 24 LTS + Docker Engine + Portainer CE/EE (Git-backed stack deployment)
- **Analytics Engine**: ClickHouse 26.8 LTS branch (`clickhouse/clickhouse-server:26.8`)
- **Distributed Coordination**: ClickHouse Keeper (3-node Raft quorum for production HA)
- **Data Lake Storage**: S3-Compatible Object Storage (MinIO for DEV/UAT, enterprise S3 for PROD) + Parquet file format
- **Data Transformation**: `dbt-clickhouse` for automated Medallion transformations
- **Observability**: Prometheus (scraping ClickHouse native metrics) + Grafana (curated dashboards) + Loki (structured logs)
- **Governance & CI/CD**: Governed promotion (`GitHub` -> `Jenkins` -> `Harbor` -> `Trivy` -> `Portainer Git Stack`), `AGENTS.md` as canonical engineering policy, strict least privilege RBAC, and zero hardcoded production credentials.

---

## User Review Required

> [!IMPORTANT]
> **Production HA vs DEV/UAT Single-Node**:
> In accordance with DOC-03, DOC-04, and DOC-05, single-host Docker Compose is strictly categorized as DEV/UAT evaluation and benchmark topology, and **must not be misrepresented as true High Availability (HA)**. True HA requires deploying the provided multi-host topology (1 Shard x 2 Replicas + 3 Keeper quorum across independent failure domains). Both Compose profiles (Single-node DEV/UAT and Multi-node HA) will be generated.

> [!WARNING]
> **No Hardcoded Secrets Policy**:
> In compliance with enterprise security rules, all configurations, Compose files, and DDL scripts will use environment variable placeholders (`${CLICKHOUSE_PASSWORD}`, `${S3_ACCESS_KEY}`, etc.) and an `.env.example` file. Never commit `.env` containing production credentials.

---

## Proposed Changes & Deliverables

```text
Enterprise-Data-Lakehouse-Platform/
├── AGENTS.md                                # [NEW] Canonical Engineering & AI-governance policy
├── README.md                                # [MODIFY] Comprehensive enterprise platform documentation
├── .env.example                             # [NEW] Template environment variables (safe placeholders)
│
├── agents/                                  # [NEW] AI Agent team roles & handoff contracts
│   ├── orchestrator.md
│   ├── solution-architect.md
│   ├── data-architect.md
│   ├── clickhouse-engineer.md
│   ├── data-pipeline-engineer.md
│   ├── platform-devops.md
│   ├── security-governance.md
│   ├── sre-observability.md
│   └── qa-validation.md
│
├── adr/                                     # [NEW] Architecture Decision Records
│   ├── 0001-storage-separation-and-parquet.md
│   ├── 0002-clickhouse-medallion-layering.md
│   ├── 0003-docker-and-portainer-git-stacks.md
│   ├── 0004-clickhouse-keeper-coordination.md
│   └── 0005-dbt-clickhouse-transformation.md
│
├── compose/                                 # [NEW] Docker Compose & Portainer Stacks
│   ├── docker-compose.dev.yml               # All-in-one DEV/UAT stack (ClickHouse, MinIO, Monitoring)
│   ├── docker-compose.prod-node1.yml        # PROD Node 1 (Replica 1 + Keeper 1)
│   ├── docker-compose.prod-node2.yml        # PROD Node 2 (Replica 2 + Keeper 2)
│   ├── docker-compose.prod-keeper3.yml      # PROD Node 3 (Keeper 3 quorum tie-breaker)
│   └── docker-compose.observability.yml     # Prometheus, Grafana, Loki stack
│
├── clickhouse/                              # [NEW] Governed ClickHouse Server Configurations
│   ├── config.d/
│   │   ├── storage_configuration.xml        # NVMe hot tier + S3/MinIO cold lake tier
│   │   ├── keeper_config.xml                # ClickHouse Keeper 3-node Raft configuration
│   │   ├── clusters.xml                     # Distributed cluster definition (1 shard, 2 replicas)
│   │   ├── prometheus.xml                   # Native Prometheus metric exporter (port 9363)
│   │   ├── network.xml                      # Network listen hosts and internal port isolation
│   │   └── logging.xml                      # Structured logging & query log retention
│   └── users.d/
│       ├── users.xml                        # User templates with password sha256/env injection
│       └── roles_and_profiles.xml           # Least-privilege roles (etl, bi_readonly, api, admin, quotas)
│
├── sql/                                     # [NEW] Database DDL & Schemas
│   ├── init/
│   │   ├── 01_databases.sql                 # raw, core, mart, serving databases
│   │   ├── 02_medallion_tables.sql          # Bronze landing, Silver conformed, Gold marts (fact_sales)
│   │   ├── 03_materialized_views.sql        # High-performance serving views & AggregatingMergeTree
│   │   └── 04_rbac_and_row_policies.sql     # Roles, Grants, Row Policies & Quotas
│
├── dbt/                                     # [NEW] dbt-clickhouse Data Transformation Project
│   ├── dbt_project.yml
│   ├── profiles.yml.example
│   ├── models/
│   │   ├── bronze/sources.yml               # Raw source contract definitions
│   │   ├── silver/silver_orders_cleaned.sql # Conformed & deduplicated models
│   │   └── gold/gold_sales_summary.sql      # Aggregated business marts
│   └── tests/
│       └── test_sales_amount_positive.sql   # Data quality integrity tests
│
├── monitoring/                              # [NEW] Observability & Alerting
│   ├── prometheus/
│   │   ├── prometheus.yml                   # Scrape targets for ClickHouse, Keeper, MinIO, Node
│   │   └── alert_rules.yml                  # Actionable alerts (query latency, merges, replication lag, keeper)
│   ├── grafana/
│   │   ├── provisioning/
│   │   │   ├── datasources/datasources.yml
│   │   │   └── dashboards/dashboards.yml
│   │   └── dashboards/
│   │       └── clickhouse_overview.json     # Curated ClickHouse & Lakehouse dashboard
│   └── loki/
│       └── loki-config.yml
│
├── runbooks/                                # [NEW] Operational Runbooks
│   ├── 01_portainer_git_stack_deployment.md # Deploying and updating stacks via Portainer
│   ├── 02_backup_and_restore_operations.md  # ClickHouse BACKUP to S3, restore verification & RTO/RPO drill
│   └── 03_troubleshooting_and_failover.md   # Replication recovery, Keeper quorum loss, partition inspection
│
└── scripts/                                 # [NEW] Maintenance & Validation Scripts
    ├── backup_clickhouse.sh                 # Governed non-blocking backup script to S3
    ├── restore_test.sh                      # Isolated non-destructive restore drill script
    └── validate_stack.sh                    # Compose YAML linter, network check, and syntax validator
```

---

## Component Details

### 1. Canonical Governance & Agent Teams (`AGENTS.md`, `agents/`)
- Establish `AGENTS.md` as required by DOC-05 and DOC-07.
- Implement the 9 primary agent specs (`orchestrator`, `solution-architect`, `data-architect`, `clickhouse-engineer`, `data-pipeline-engineer`, `platform-devops`, `security-governance`, `sre-observability`, `qa-validation`).
- Document explicit human review gates for destructive actions, credential changes, and production releases.

### 2. Infrastructure & Portainer Deployment (`compose/`, `.env.example`)
- **DEV/UAT Compose**: ClickHouse 26.8 LTS, MinIO S3 object storage with auto-created lakehouse buckets (`lake-landing`, `lake-bronze`, `lake-archive`, `lake-backup`), Portainer Agent, Prometheus, Grafana.
- **Production HA Compose**: Clean separation across 3 nodes to eliminate single point of failure (1 Shard x 2 Replicas with ClickHouse Keeper Raft quorum on port 9181/9234).
- Internal network segmentation (`data_ingestion`, `data_backend`, `data_storage`, `observability`, `management`).

### 3. ClickHouse Storage & Engine Design (`clickhouse/`, `sql/`)
- **Storage Tiering**: Configured in `storage_configuration.xml` using `default` (local NVMe) and `s3_cold` (S3/MinIO) disks, bound to `hot_to_cold` volume policy with automatic TTL movement.
- **MergeTree Best Practices**:
  - Fact tables partitioned by month `PARTITION BY toYYYYMM(sale_date)` to prevent part explosion.
  - Sorting keys `ORDER BY (sale_date, branch_id, product_id, customer_id)` aligned with query access patterns.
  - Required metadata tracking: `_source_system`, `_source_table`, `_ingested_at`, `_source_updated_at`, `_batch_id`, `_record_hash`, `_is_deleted`.
  - CDC deduplication handled via `ReplacingMergeTree(_source_updated_at, _is_deleted)`.

### 4. Data Transformation (`dbt/`)
- Setup complete `dbt-clickhouse` project configured for Medallion architecture.
- Bronze to Silver deduplication and conformed transformation, Silver to Gold rollup tables, and automated schema/quality test assertions.

### 5. Observability & Operations (`monitoring/`, `runbooks/`, `scripts/`)
- Native ClickHouse metric export into Prometheus.
- Actionable alert rules: High Query Errors, Memory Limit, Merge Backlog / Too Many Parts (>300 parts), Replication Queue Lag, Keeper Quorum Degradation, and Backup Stale alert (>24h).
- Automated backup script using ClickHouse native `BACKUP TABLE ... TO S3(...)` syntax.
- Non-destructive restore drill script verifying checksums and row count reconciliation.

---

## Verification Plan

### Automated Checks
1. **YAML Syntax Validation**: Run `docker compose -f compose/docker-compose.dev.yml config` and production compose files to ensure syntactically valid Compose V2 configurations.
2. **SQL Syntax & Parser Validation**: Validate SQL DDL files against ClickHouse syntax conventions.
3. **Shell Script Syntax Validation**: Validate bash scripts (`backup_clickhouse.sh`, `restore_test.sh`, `validate_stack.sh`) using bash syntax parser (`bash -n`).
4. **Secret Scanning**: Verify no hardcoded credentials or private keys exist across any file.

### Manual / Operational Verification
- Provide instructions for starting DEV/UAT stack via `docker compose -f compose/docker-compose.dev.yml up -d` or Portainer Git Stack.
- Verify ClickHouse responds on HTTP 8123 and native 9000.
- Verify MinIO bucket creation and S3 storage tier connectivity.
