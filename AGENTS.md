# AGENTS.md - Enterprise Engineering & AI-Governance Policy

> **Authority**: Primary engineering and AI-governance policy for the Enterprise Data Lakehouse Platform repository. All human contributors, automated pipelines, and AI coding agents MUST strictly adhere to this document.

**Document Baseline**: 2026-09-03 | **Target Runtime**: Ubuntu 24 LTS, Docker Engine, Portainer, ClickHouse 26.8 LTS

---

## 1. Fundamental Principles

1. **AI Agents are Engineering Assistants, Not Autonomous Production Authorities**:
   - AI agents analyze, draft, generate, validate in sandbox environments, and produce reviewable artifacts.
   - AI agents MUST NOT independently execute production deployments, alter production firewall rules, delete production databases/volumes, or approve their own security exceptions.
2. **Zero-Trust Secret Handling**:
   - Never embed passwords, API tokens, private keys, production connection strings, or customer data into Git repositories, Docker Compose files, Dockerfiles, prompt templates, logs, or documentation.
   - Use environment variable placeholders (`${VAR_NAME}`) and secure secret management.
3. **No Unvalidated Claims**:
   - Never state that a test, benchmark, backup, or vulnerability scan has succeeded unless the validation command was actually executed and the actual output is reported.
   - Use `TBD` for all unresolved organization-specific infrastructure parameters (such as actual IP addresses, external DNS names, and business-approved RPO/RTO).
4. **Separation of Concerns & Human Gates**:
   - Changes require review separation: authoring agents must have their work challenged/verified by validation agents or human domain owners.
   - Production promotion, destructive database migrations, and credential rotations require explicit human sign-off.

---

## 2. Platform Technical Baseline

- **Operating System**: Ubuntu 24 LTS (Hardened, NTP synchronized)
- **Containerization**: Docker Engine + Docker Compose (Compose V2)
- **Operations UI**: Portainer CE/EE (Operated via Git-backed Stacks; never as an ad-hoc unmanaged production bypass)
- **Analytics Engine**: ClickHouse 26.8 LTS (Explicitly pinned patch/digest; never use bare `:latest` in production)
- **Coordination**: ClickHouse Keeper (3-node Raft quorum across independent failure domains for HA)
- **Data Lake Storage**: S3-Compatible Object Storage (MinIO for DEV/UAT; enterprise S3 for PROD) with Apache Parquet
- **Transformation**: `dbt-clickhouse` (Version-controlled models, tests, and lineage)
- **Observability**: Prometheus, Grafana, and Loki (Native metrics scraping and structured log aggregation)
- **CI/CD Governance**: GitHub -> Jenkins -> Harbor -> Trivy -> Portainer Git Stack

---

## 3. High Availability vs. Development Boundary

> [!CAUTION]
> **Single-Host Deployments Are NOT High Availability**:
> Running multiple containers (or replicas) on a single physical host or VM is categorized strictly as **DEV/UAT** for functional testing and benchmarking. It does NOT protect against host, disk, or network failure.
> Production High Availability (HA) MUST be deployed across at least 3 distinct failure domains (1 Shard x 2 Replicas + 3 Keeper quorum members).

---

## 4. ClickHouse Architecture & Modeling Guardrails

1. **Medallion Database Separation**:
   - `raw`: Append-only, source-aligned landing/raw data with technical metadata columns.
   - `core`: Cleansed, conformed, deduplicated, and normalized silver layer.
   - `mart`: Business facts, dimensions, and pre-aggregated gold analytical models.
   - `serving`: High-speed views, Materialized Views, and API endpoints.
2. **Technical Metadata Standard**:
   Every ingested row in `raw` and `core` must include:
   - `_source_system` (LowCardinality(String))
   - `_source_table` (LowCardinality(String))
   - `_ingested_at` (DateTime64(3))
   - `_source_updated_at` (DateTime64(3))
   - `_batch_id` (String)
   - `_record_hash` (FixedString(32) or String)
   - `_is_deleted` (UInt8)
3. **Partition & Sorting Key Rules**:
   - `PARTITION BY` MUST NOT use high-cardinality fields (e.g., UUID, customer_id, timestamp). Use monthly or daily granularity (e.g., `toYYYYMM(event_date)`).
   - `ORDER BY` MUST be selected based on actual query filter/group-by patterns to maximize primary index efficiency.
   - CDC deduplication MUST use `ReplacingMergeTree(_source_updated_at, _is_deleted)` with explicit `FINAL` or argMax serving logic.

---

## 5. Security & Access Control Guardrails

1. **Least Privilege Roles**:
   - `platform_admin`: Superuser for break-glass and cluster administration only.
   - `data_engineer`: DDL and transformation permissions on `raw`, `core`, and `mart`.
   - `etl_service`: Write-only to `raw` landing tables.
   - `bi_readonly`: Read-only access to `mart` and `serving` databases only.
   - `api_service`: Read-only access to specific serving views.
   - `monitoring_service`: Read-only access to system tables (`system.metrics`, `system.events`, `system.parts`, etc.).
   - `backup_service`: Minimal privileges for backup/restore execution.
2. **Network Isolation**:
   - Restrict ClickHouse HTTP (8123) and Native (9000) to internal Docker networks and trusted reverse proxies.
   - Restrict Keeper ports (9181, 9234) exclusively to the cluster backend network.
   - Restrict Portainer admin ports (9000/9443) to the management VPN.

---

## 6. Backup, Recovery & DR Verification

1. **Non-Negotiable Verification**:
   - A backup is considered a theoretical assumption until a non-destructive restore drill has been successfully demonstrated and verified.
2. **RPO & RTO Targets**:
   - RPO target: <= 1 hour (subject to business owner sign-off).
   - RTO target: <= 4 hours (subject to business owner sign-off).
3. **Backup Destination**:
   - Backups must be written directly to independent S3-compatible object storage, never kept solely on ClickHouse local disks.

---

## 7. Change Management & Verification Protocol

For all modifications to Compose files, SQL DDL, or configurations:
1. **Linter & Syntax Check**: Execute syntax checks (`docker compose config`, `clickhouse-client --dry-run` or parser checks).
2. **Impact Assessment**: Document backward compatibility, storage volume impact, and rollback limitations.
3. **Handoff Report**: Every agent output must conclude with the standard Handoff Contract:
   - Scope & Sources Inspected
   - Assumptions & Decisions
   - Security & Operational Impact
   - Validation Commands & Results
   - Remaining TBDs & Residual Risks
   - Human Approval Required
