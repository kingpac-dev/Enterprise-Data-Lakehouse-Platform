# Enterprise Data Lakehouse System Architecture Blueprint

> Logical, data, deployment, security, observability, recovery, and operations architecture

**Document:** DOC-03 | Enterprise Data Lakehouse Platform

**Architecture & Planning Baseline | 2026-09-03**

*Status: Design baseline - organization-specific `TBD` values require human approval.*

> **Governance:** Repository `AGENTS.md` is the primary engineering and AI-governance policy. This document is a design baseline and must not be treated as evidence of production validation, security verification, HA testing, or recovery certification.

# Document Control

| **Item**          | **Value**                                                                                               |
|-------------------|---------------------------------------------------------------------------------------------------------|
| Document          | System Architecture Blueprint                                                                           |
| Purpose           | Provide the authoritative conceptual and logical blueprint for the enterprise data lakehouse platform.  |
| Audience          | Architects, platform engineers, data engineers, security, SRE, developers, and implementation partners. |
| Platform baseline | Ubuntu 24 LTS + Docker Engine + Portainer + ClickHouse 26.8 LTS branch                                  |
| Status            | Design baseline                                                                                         |
| Date              | 2026-09-03                                                                                              |
| Governance source | Repository `AGENTS.md` is the primary engineering and AI-governance policy.                               |

> **Control note:** technical values marked TBD are intentionally unresolved until workload, security, business continuity, and infrastructure requirements are formally approved.

# 1. Architecture Principles

- Lake storage and analytical compute are logically separable.

- Object storage is the durable Landing/Bronze/Archive layer.

- ClickHouse is optimized for curated analytical workloads and serving, not OLTP transaction processing.

- Configuration is version controlled and promoted through governed CI/CD.

- Security is defense-in-depth across identity, network, runtime, data, and operations.

- Scale vertically and optimize schemas before adding shards; add distributed complexity only when metrics justify it.

- Every production design includes observability and recovery as first-class architecture components.

## Baseline Assumptions and Constraints

- Initial self-managed runtime uses Ubuntu 24 LTS, Docker Engine, Docker Compose, and Portainer.

- ClickHouse is the high-performance OLAP and curated serving engine; object storage remains the durable raw/long-term lake layer.

- DEV/UAT may begin as single-node for evaluation and benchmarking; this topology is not considered high availability.

- Production HA is designed around separate failure domains with ClickHouse replication and a three-member ClickHouse Keeper quorum.

- Git is the configuration source of truth; Jenkins/CI controls validation and promotion; Harbor is the target enterprise registry where available.

- Prometheus, Grafana, and Loki form the baseline observability stack.

- Organization-specific values that have not been approved are marked TBD rather than assumed.

# 2. Enterprise Logical Architecture


```text
Enterprise Data Sources

|-- SQL Server / PostgreSQL / MySQL / MongoDB

|-- ERP & Business Applications

|-- REST APIs / Files / IoT / Logs

v

Ingestion

|-- Batch: Airbyte / Custom Workers

|-- CDC: Debezium

|-- Streaming: Kafka / Redpanda

v

S3-Compatible Data Lake

|-- landing/

|-- bronze/

|-- archive/

v

ClickHouse

|-- raw

|-- core (Silver)

|-- mart (Gold)

|-- serving

v

Power BI / Grafana / APIs / Analysts / AI & ML
```


# 3. Data Architecture Blueprint


| **Layer**     | **Namespace / Path**                                  | **Contract**                                                 |
|---------------|-------------------------------------------------------|--------------------------------------------------------------|
| Landing       | s3://\<lake\>/landing/\<source\>/\<entity\>/\<date\>/ | Immutable source receipt; source file and checksum retained. |
| Bronze        | s3://\<lake\>/bronze/\<domain\>/\<entity\>/           | Source-aligned Parquet; ingestion metadata appended.         |
| Raw           | ClickHouse raw.\*                                     | Fast staging/ingestion when native ClickHouse is useful.     |
| Core / Silver | ClickHouse core.\*                                    | Cleaned, deduplicated, conformed entities and keys.          |
| Mart / Gold   | ClickHouse mart.\*                                    | Business facts, dimensions, KPI aggregates.                  |
| Serving       | ClickHouse serving.\*                                 | Dashboard/API optimized tables/views/materialized views.     |
| Archive       | s3://\<lake\>/archive/...                             | Cold historical retention with lifecycle policy.             |

## 3.1 Standard Technical Metadata


```text
_source_system

_source_table

_ingested_at

_source_updated_at

_batch_id

_record_hash

_is_deleted
```


# 4. ClickHouse Logical Database Blueprint


```text
ClickHouse

|-- raw

| |-- erp_sales_raw

| |-- production_raw

| `-- application_events_raw

|-- core

| |-- sales

| |-- production

| `-- inventory

|-- mart

| |-- fact_sales

| |-- fact_production

| |-- fact_inventory

| |-- dim_customer

| `-- dim_product

`-- serving

|-- sales_daily

|-- production_daily

|-- inventory_current

`-- executive_kpi
```


| **Workload**                 | **Preferred Engine Pattern**                                     |
|------------------------------|------------------------------------------------------------------|
| Append-only facts/events     | MergeTree                                                        |
| Replicated production tables | ReplicatedMergeTree                                              |
| CDC/versioned entities       | ReplacingMergeTree with explicit version semantics               |
| Pre-aggregated state         | AggregatingMergeTree                                             |
| Additive summaries           | SummingMergeTree when semantics are valid                        |
| Distributed access           | Distributed table/routing layer only when sharding is introduced |

# 5. Deployment Blueprint


## 5.1 DEV/UAT Baseline


```text
Ubuntu 24 LTS Host

|-- Docker Engine

|-- Portainer

|-- ClickHouse

|-- S3-Compatible Object Storage

|-- Prometheus

|-- Grafana

`-- Loki

Classification: evaluation / benchmark topology, NOT HA.
```


## 5.2 Production HA Baseline


```text
Failure Domain / Host 01

|-- ClickHouse Replica 01

`-- Keeper 01

Failure Domain / Host 02

|-- ClickHouse Replica 02

`-- Keeper 02

Failure Domain / Host 03

`-- Keeper 03

Shared / Independent Services

|-- S3-Compatible Object Storage

|-- Monitoring / Logging

`-- CI/CD / Registry
```


> **Production baseline:** 1 shard x 2 ClickHouse replicas + 3 Keeper members. Do not describe multiple containers on a single Docker host as high availability.

# 6. Network and Security Zones

| **Zone / Network** | **Typical Members**                        | **Allowed Direction**                               |
|--------------------|--------------------------------------------|-----------------------------------------------------|
| data_ingestion     | Airbyte, Debezium, workers, Kafka/Redpanda | Sources -\> ingestion -\> lake/raw                  |
| data_backend       | ClickHouse nodes                           | Trusted clients/ingestion -\> ClickHouse only       |
| data_storage       | ClickHouse, ingestion, object storage      | Controlled storage access only                      |
| observability      | Prometheus, Grafana, Loki, exporters       | Monitoring -\> runtime; logs/metrics -\> monitoring |
| management         | Portainer, Jenkins deployment endpoint     | Restricted admin/CI access only                     |

- No unnecessary public exposure.

- TLS for sensitive traffic.

- Firewall allow-listing between zones.

- Separate human and service identities.

- Production administrative interfaces remain internal unless explicitly justified.

# 7. Security Architecture


| **Control Plane**        | **Required Controls**                                                                        |
|--------------------------|----------------------------------------------------------------------------------------------|
| Identity                 | Named users for humans; service accounts for workloads; least privilege; periodic review.    |
| ClickHouse authorization | RBAC, role grants, row policies where required, quotas/settings profiles.                    |
| Secrets                  | No secrets in Git/images; protected runtime injection; future Vault/equivalent if justified. |
| Network                  | Segmentation, firewall allow-list, internal admin endpoints, TLS.                            |
| Container supply chain   | Pinned images, Harbor, Trivy scan, SBOM/signing roadmap.                                     |
| Operations               | Auditable deployment, approval gates, emergency change reconciliation.                       |
| Data                     | Classification, retention, masking/row policy as required, minimal PII in logs.              |

# 8. Observability Blueprint

| **Signal**   | **Examples**                                                                       |
|--------------|------------------------------------------------------------------------------------|
| Availability | Service health, container restart count, Keeper connectivity, replica availability |
| Query        | QPS, error rate, P95/P99 latency, query memory, rejected/queued queries            |
| Storage      | Disk usage, part count, merge backlog, object storage errors                       |
| Replication  | Replica lag, queue size, read-only state, Keeper session health                    |
| Ingestion    | Rows/sec, batch duration, consumer lag, failed batches, retry count                |
| Recovery     | Last successful backup, backup duration/size, last restore drill                   |

# 9. CI/CD and Portainer Blueprint


```text
Developer / Data Engineer

v

GitHub Pull Request

v

Jenkins Validation

|-- lint / syntax

|-- tests

|-- Trivy / secret scan

|-- image build / SBOM

v

Harbor Immutable Image

v

Approval Gate

v

Portainer Git Stack / Controlled Deployment

v

Health + Smoke + Observability Verification
```


Portainer is the controlled operations interface and may deploy Git-backed stacks. It must not become an alternative manual production deployment path that bypasses review, security scanning, or release approval.

# 10. Backup and DR Blueprint

- Backups stored outside ClickHouse compute hosts.

- Full and incremental strategy based on dataset size and recovery requirements.

- Off-site or independent failure-domain copy recommended.

- Restore tests performed on a defined schedule.

- RPO = TBD; proposed starting discussion \<= 1 hour.

- RTO = TBD; proposed starting discussion \<= 4 hours.

- A backup is not considered operationally reliable until a restore test is demonstrated.

# 11. Architecture Evolution Path

| **Trigger**                                             | **Potential Evolution**                                                          |
|---------------------------------------------------------|----------------------------------------------------------------------------------|
| More engines need shared tables                         | Add Apache Iceberg + catalog after operational justification.                    |
| Near-real-time business SLA                             | Introduce Debezium + Kafka/Redpanda CDC/streaming.                               |
| Single-node capacity exhausted after tuning             | Add replicated cluster / sharding based on benchmark.                            |
| Many teams need self-service                            | Add data catalog, lineage, policy automation, templates, data product ownership. |
| Container estate/scale exceeds Docker operational model | Evaluate Kubernetes/GitOps/Argo CD, not before.                                  |
| AI/ML workloads need governed access                    | Add feature/embedding pipelines, semantic contracts, controlled tool APIs.       |

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
