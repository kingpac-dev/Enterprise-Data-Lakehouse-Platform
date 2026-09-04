# Enterprise Data Lakehouse Technical Design & Specifications

> Implementation-level technical requirements for ClickHouse, object storage, networking, security, CI/CD, observability, and disaster recovery

**Document:** DOC-04 | Enterprise Data Lakehouse Platform

**Architecture & Planning Baseline | 2026-09-03**

*Status: Design baseline - organization-specific `TBD` values require human approval.*

> **Governance:** Repository `AGENTS.md` is the primary engineering and AI-governance policy. This document is a design baseline and must not be treated as evidence of production validation, security verification, HA testing, or recovery certification.

# Document Control

| **Item**          | **Value**                                                                                                     |
|-------------------|---------------------------------------------------------------------------------------------------------------|
| Document          | Technical Design & Technical Specifications                                                                   |
| Purpose           | Translate the approved blueprint into implementation-level technical requirements and configuration patterns. |
| Audience          | Platform engineering, data engineering, ClickHouse engineers, DevOps, security, SRE, QA, and operations.      |
| Platform baseline | Ubuntu 24 LTS + Docker Engine + Portainer + ClickHouse 26.8 LTS branch                                        |
| Status            | Design baseline                                                                                               |
| Date              | 2026-09-03                                                                                                    |
| Governance source | Repository `AGENTS.md` is the primary engineering and AI-governance policy.                                     |

> **Control note:** technical values marked TBD are intentionally unresolved until workload, security, business continuity, and infrastructure requirements are formally approved.

# 1. Specification Status and Requirement Language

The terms MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY express requirement strength inside this design baseline. Values marked TBD are not final requirements until approved.

## Baseline Assumptions and Constraints

- Initial self-managed runtime uses Ubuntu 24 LTS, Docker Engine, Docker Compose, and Portainer.

- ClickHouse is the high-performance OLAP and curated serving engine; object storage remains the durable raw/long-term lake layer.

- DEV/UAT may begin as single-node for evaluation and benchmarking; this topology is not considered high availability.

- Production HA is designed around separate failure domains with ClickHouse replication and a three-member ClickHouse Keeper quorum.

- Git is the configuration source of truth; Jenkins/CI controls validation and promotion; Harbor is the target enterprise registry where available.

- Prometheus, Grafana, and Loki form the baseline observability stack.

- Organization-specific values that have not been approved are marked TBD rather than assumed.

# 2. Platform Baseline

| **Component**     | **Baseline**                   | **Specification**                                                                          |
|-------------------|--------------------------------|--------------------------------------------------------------------------------------------|
| Operating system  | Ubuntu 24 LTS                  | Hardened server/VM; time sync; approved patching; dedicated data volumes recommended.      |
| Container runtime | Docker Engine + Docker Compose | Production configuration stored in Git; no secrets embedded in Compose.                    |
| Operations UI     | Portainer                      | Restricted management network; controlled operations; Git-backed stack preferred.          |
| Analytics         | ClickHouse 26.8 LTS branch     | Pin explicit approved patch/image digest; do not use latest as sole production identifier. |
| Coordination      | ClickHouse Keeper              | 3 members for initial HA design; members distributed across failure domains.               |
| Object storage    | S3-compatible                  | Durable Landing/Bronze/Archive/Backup; product selection TBD.                              |
| Transformation    | dbt-clickhouse                 | Version-controlled models and tests.                                                       |
| Observability     | Prometheus/Grafana/Loki        | Metrics, dashboards, searchable structured logs and alerting.                              |
| CI/CD             | GitHub/Jenkins/Harbor/Trivy    | Immutable promotion, vulnerability scan, audit trail.                                      |

# 3. Environment and Host Specifications

| **Environment**          | **CPU**             | **RAM**    | **Local Storage**           | **Topology**                       |
|--------------------------|---------------------|------------|-----------------------------|------------------------------------|
| DEV                      | 4-8 vCPU            | 16-32 GB   | \>= 500 GB SSD              | Single node acceptable             |
| UAT                      | 8-16 vCPU           | 32-64 GB   | 1-2 TB NVMe recommended     | Single node for benchmark; not HA  |
| PROD per ClickHouse node | 16-32+ vCPU         | 64-128+ GB | 2-4+ TB NVMe starting point | 1 shard x 2 replicas initially     |
| Keeper member            | TBD after benchmark | TBD        | Durable coordination volume | 3 separate members/failure domains |

> **Sizing note:** These hardware values are sizing starting points only. Final production sizing MUST be supported by a representative benchmark that measures query concurrency, ingestion rate, data volume, compression, merges, storage I/O, and recovery behavior.

# 4. Container and Stack Structure


```text
Portainer / Compose Stacks

|-- data-platform-core

| |-- clickhouse

| `-- keeper (where applicable)

|-- data-platform-storage

| `-- s3-compatible-object-storage

|-- data-platform-ingestion

| |-- airbyte

| |-- debezium

| `-- kafka-or-redpanda

|-- data-platform-transform

| |-- dbt-runner

| `-- airflow-or-dagster (optional)

`-- data-platform-observability

|-- prometheus

|-- grafana

`-- loki
```


## 4.1 Container Requirements

- Images MUST be explicitly versioned and SHOULD be pinned by digest for production.

- Containers MUST NOT contain embedded passwords, tokens, private keys, or production connection strings.

- Persistent ClickHouse data MUST be on explicit durable volumes/mounts with documented ownership and backup behavior.

- Health checks SHOULD be configured where technically meaningful.

- Resource limits/reservations SHOULD be benchmark-driven; avoid arbitrary limits that create memory pressure or OOM behavior.

- Logs SHOULD be structured and MUST avoid credentials and unnecessary personal data.

# 5. ClickHouse Server and Schema Design

## 5.1 Database Namespaces


```text
raw

core

mart

serving
```


## 5.2 MergeTree Design Rules

- PARTITION BY SHOULD use a low-cardinality time/domain key appropriate to retention and maintenance; monthly partitioning is a common starting pattern for time-series facts.

- ORDER BY MUST be designed from dominant filter/group patterns and data locality, not copied blindly from OLTP primary keys.

- High-cardinality identifiers SHOULD NOT be used as standalone partition keys.

- ReplacingMergeTree version/delete semantics MUST be explicitly defined for CDC models; do not assume immediate deduplication semantics.

- Materialized views SHOULD be used selectively for proven serving/aggregation requirements.

## 5.3 Example Fact Table


```sql
CREATE TABLE mart.fact_sales

(

sale_date Date,

sale_datetime DateTime64(3),

customer_id UInt64,

product_id UInt64,

branch_id UInt32,

quantity Decimal(18, 3),

amount Decimal(18, 2),

_source_system LowCardinality(String),

_ingested_at DateTime64(3)

)

ENGINE = MergeTree

PARTITION BY toYYYYMM(sale_date)

ORDER BY (sale_date, branch_id, product_id, customer_id);
```


# 6. Object Storage Specification


```text
<lake-bucket>/

|-- landing/<source>/<entity>/YYYY/MM/DD/

|-- bronze/<domain>/<entity>/YYYY/MM/DD/

|-- archive/<domain>/<entity>/...

|-- backup/clickhouse/...

`-- lakehouse/iceberg/... # optional future
```


- Landing data SHOULD be immutable once accepted.

- Parquet is the initial preferred analytical file format.

- Bucket/path naming MUST be stable, lowercase where practical, and independent of one query engine.

- Encryption, versioning, object lock/legal hold, and lifecycle configuration are organization-specific TBD controls.

- Credentials MUST be injected through approved secret mechanisms and scoped to required buckets/prefixes.

# 7. Ingestion and Data Contract Specification

| **Field**           | **Requirement**                                                   |
|---------------------|-------------------------------------------------------------------|
| \_source_system     | MUST identify the originating system.                             |
| \_source_table      | SHOULD identify source entity/table when applicable.              |
| \_ingested_at       | MUST record platform ingestion timestamp.                         |
| \_source_updated_at | SHOULD capture source change timestamp when available.            |
| \_batch_id          | MUST identify a replayable batch/run for batch pipelines.         |
| \_record_hash       | SHOULD support change/reconciliation logic where applicable.      |
| \_is_deleted        | MUST be defined for CDC delete semantics when CDC is implemented. |

## 7.1 Pipeline Requirements

- Pipelines MUST be idempotent or explicitly document duplicate-handling behavior.

- Retries MUST be bounded and observable.

- Source extraction and target load counts SHOULD be reconciled for critical datasets.

- Schema evolution behavior MUST be documented per source.

- Failed records SHOULD be quarantined with enough metadata for replay without exposing sensitive data in logs.

# 8. Network Specifications

| **Traffic**               | **Default / Common Port** | **Rule**                                                                                        |
|---------------------------|---------------------------|-------------------------------------------------------------------------------------------------|
| ClickHouse HTTP interface | 8123 by default           | Internal trusted clients only; use TLS endpoint/configuration for sensitive production traffic. |
| ClickHouse native TCP     | 9000 by default           | Do not expose broadly; restrict to trusted clients/nodes.                                       |
| ClickHouse Keeper client  | 9181 commonly configured  | Cluster/coordination network only.                                                              |
| Keeper Raft peer traffic  | Configuration-defined     | Keeper members only; explicit allow-list.                                                       |
| Prometheus scrape         | Configuration-defined     | Monitoring network only.                                                                        |
| Portainer UI/API          | Deployment-specific       | Management network; restricted administration.                                                  |
| Kafka/Redpanda            | Deployment-specific       | Ingestion network only; defer until Phase 9 if not required.                                    |

Port values are configuration-dependent and MUST be verified against the actual deployed configuration before firewall implementation.

# 9. Identity and Authorization Specification

| **Identity**       | **Purpose**                         | **Minimum Access**                                                               |
|--------------------|-------------------------------------|----------------------------------------------------------------------------------|
| platform_admin     | Break-glass/platform administration | Restricted privileged administration; audited.                                   |
| data_engineer      | Schema/model development            | Approved raw/core/mart development privileges; no broad platform administration. |
| etl_service        | Ingestion automation                | Write only to approved raw/staging targets; read source/lake prefixes as needed. |
| bi_readonly        | BI tools                            | Read approved mart/serving objects only.                                         |
| api_service        | Application serving                 | Read only specific serving datasets/views.                                       |
| monitoring_service | Metrics collection                  | Read operational/system metrics only.                                            |
| backup_service     | Backup automation                   | Minimum privileges required for backup target and ClickHouse backup operations.  |

- Shared default/admin accounts MUST NOT be used by BI or application workloads.

- Privileged roles MUST be reviewed periodically.

- Row policies SHOULD be used where row-level segregation is required.

- Quotas/settings profiles SHOULD protect the platform from unbounded consumer workloads.

# 10. Observability Technical Specification

| **Category** | **Required Measurements**                                                       |
|--------------|---------------------------------------------------------------------------------|
| Query        | QPS, errors, latency, memory, concurrency/queues, top expensive queries         |
| System       | CPU, memory, filesystem, network, container restarts                            |
| MergeTree    | Active parts, merge backlog, insert rate, mutation/move status as applicable    |
| Replication  | Replica availability/lag, replication queue, read-only state                    |
| Keeper       | Connectivity, leader/quorum health, latency, outstanding requests where exposed |
| Ingestion    | Rows/sec, batch duration, failures, consumer lag, source freshness              |
| Backup       | Last success, duration, bytes, failure, restore-test date                       |

## 10.1 Alert Design

- Alerts MUST be actionable and mapped to a runbook/owner.

- Capacity alerts SHOULD warn before hard exhaustion.

- Replication/Keeper alerts MUST distinguish transient lag from quorum/availability loss.

- Backup failure and overdue restore-test alerts MUST be treated as recovery-control failures.

# 11. Backup and Recovery Specification

| **Control**        | **Specification**                                                                             |
|--------------------|-----------------------------------------------------------------------------------------------|
| Backup destination | Independent S3-compatible/object storage location, not only local ClickHouse disk.            |
| Backup types       | Full plus incremental where operationally appropriate.                                        |
| RPO                | TBD; proposed discussion target \<= 1 hour for critical curated data.                         |
| RTO                | TBD; proposed discussion target \<= 4 hours.                                                  |
| Retention          | TBD by business/legal requirement.                                                            |
| Restore test       | At least quarterly proposed; final frequency TBD.                                             |
| Evidence           | Record start/end time, recovered scope, integrity checks, measured RPO/RTO, failures/actions. |

# 12. CI/CD Technical Flow


```text
Checkout

-> Validate YAML / Compose / configuration

-> Lint / unit tests / dbt tests (as applicable)

-> Secret & vulnerability scan

-> Build container image

-> Container scan

-> Generate SBOM

-> Push immutable image to Harbor

-> Approval Gate

-> Deploy approved stack/config

-> Health checks

-> Smoke / data checks

-> Observe

-> Roll back to previous immutable version when technically safe
```


Database/schema changes require an expand/contract or other documented compatibility strategy. Automatic rollback MUST NOT be promised for irreversible data migrations.

# 13. Non-Functional Specifications

| **NFR**         | **Specification / Target**                                                                                     |
|-----------------|----------------------------------------------------------------------------------------------------------------|
| Availability    | TBD by workload; production topology designed to remove a single ClickHouse node as a single point of failure. |
| Performance     | Critical query P95/P99 targets TBD after representative benchmark.                                             |
| Scalability     | Scale up/tune first; add replicas/shards from measured bottlenecks.                                            |
| Security        | Least privilege, TLS, restricted admin interfaces, vulnerability/secret scanning, auditable deployment.        |
| Recoverability  | Documented backup/restore with measured restore evidence.                                                      |
| Maintainability | Git-managed config, ADRs, reusable stack/templates, runbooks, consistent naming.                               |
| Observability   | Metrics/logs/alerts for query, system, replication, ingestion, storage, backup.                                |
| Data governance | Classification, ownership, retention, metadata, and business definition required for production datasets.      |

# 14. Technical Acceptance Tests

| **Test**                     | **Pass Evidence**                                                                 |
|------------------------------|-----------------------------------------------------------------------------------|
| Fresh installation           | Environment can be recreated from approved Git/config and immutable images.       |
| Ingestion replay             | Same batch can be safely retried according to documented idempotency semantics.   |
| Schema/model test            | dbt/data checks pass for agreed critical models.                                  |
| Performance benchmark        | Approved query suite meets target or documented capacity action exists.           |
| Node failure                 | Production HA behavior validated without misrepresenting single-host tests as HA. |
| Keeper quorum                | Loss/recovery scenarios validated in a safe non-production exercise.              |
| Backup/restore               | Dataset/database restoration executed and reconciled.                             |
| Access control               | BI/API/service accounts cannot access unauthorized databases/rows.                |
| Deployment rollback/recovery | Previous immutable stack/app version restored when technically reversible.        |

# References

- ClickHouse 26.8 LTS release overview: https://presentations.clickhouse.com/2026-release-26.8/

- ClickHouse official packages / release channels: https://packages.clickhouse.com/

- ClickHouse documentation: https://clickhouse.com/docs

- ClickHouse Keeper: https://clickhouse.com/clickhouse/keeper

- ClickHouse Amazon S3 integration: https://clickhouse.com/integrations/amazon_s3

- ClickHouse integrations catalog: https://clickhouse.com/integrations

- Portainer: Add a new Docker stack / Git repository deployment: https://docs.portainer.io/sts/user/docker/stacks/add

- Portainer access control: https://docs.portainer.io/advanced/access-control

External references were reviewed for this document set on 2026-09-03. Product behavior and supported patch versions must be re-verified before production implementation.
