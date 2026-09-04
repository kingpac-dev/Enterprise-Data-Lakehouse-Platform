# Enterprise Data Lakehouse Research & Analysis Report

> Research and feasibility analysis for the Enterprise Data Lakehouse Platform with ClickHouse on Portainer.io Docker

**Document:** DOC-01 | Enterprise Data Lakehouse Platform

**Architecture & Planning Baseline | 2026-09-03**

*Status: Design baseline - organization-specific `TBD` values require human approval.*

> **Governance:** Repository `AGENTS.md` is the primary engineering and AI-governance policy. This document is a design baseline and must not be treated as evidence of production validation, security verification, HA testing, or recovery certification.

# Document Control

| **Item**          | **Value**                                                                                                           |
|-------------------|---------------------------------------------------------------------------------------------------------------------|
| Document          | Research and Analysis Report                                                                                        |
| Purpose           | Evaluate the technical approach, architecture options, feasibility, risks, and recommended enterprise baseline.     |
| Audience          | Enterprise architecture, MIS/IT leadership, data engineering, platform engineering, security, and project sponsors. |
| Platform baseline | Ubuntu 24 LTS + Docker Engine + Portainer + ClickHouse 26.8 LTS branch                                              |
| Status            | Design baseline                                                                                                     |
| Date              | 2026-09-03                                                                                                          |
| Governance source | Repository `AGENTS.md` is the primary engineering and AI-governance policy.                                           |

> **Control note:** technical values marked TBD are intentionally unresolved until workload, security, business continuity, and infrastructure requirements are formally approved.

# 1. Executive Summary

The recommended architecture is a Lakehouse + ClickHouse Acceleration model. Durable raw and historical data remains in S3-compatible object storage, while ClickHouse provides high-performance OLAP, curated Silver/Gold models, data marts, materialized views, and serving datasets for BI, APIs, and future AI workloads.

The recommended implementation path intentionally starts with a simple Docker/Portainer UAT platform for benchmarking and operational learning. Production high availability is a separate topology that requires replicated ClickHouse nodes and ClickHouse Keeper members distributed across separate failure domains.

> **Research conclusion:** use ClickHouse as the analytics/serving engine, not as the only durable storage layer. Keep the lake independent so that future engines, governance tools, or AI workloads can reuse the same durable datasets.

# 2. Research Objectives

- Determine whether ClickHouse is suitable as the analytical core of an enterprise data lakehouse.

- Define a deployment model compatible with existing Docker and Portainer operations.

- Compare batch, CDC, streaming, transformation, storage, and observability alternatives.

- Define an incremental roadmap that avoids premature Kubernetes or unnecessary platform complexity.

- Identify security, recovery, performance, governance, and operational risks before production adoption.

## Baseline Assumptions and Constraints

- Initial self-managed runtime uses Ubuntu 24 LTS, Docker Engine, Docker Compose, and Portainer.

- ClickHouse is the high-performance OLAP and curated serving engine; object storage remains the durable raw/long-term lake layer.

- DEV/UAT may begin as single-node for evaluation and benchmarking; this topology is not considered high availability.

- Production HA is designed around separate failure domains with ClickHouse replication and a three-member ClickHouse Keeper quorum.

- Git is the configuration source of truth; Jenkins/CI controls validation and promotion; Harbor is the target enterprise registry where available.

- Prometheus, Grafana, and Loki form the baseline observability stack.

- Organization-specific values that have not been approved are marked TBD rather than assumed.

# 3. Technology Findings

## 3.1 ClickHouse Release Baseline

ClickHouse 26.8 is a long-term-support release branch. The official package repository listed 26.8.2.7 as the current stable/LTS patch at the time of review. Production deployments should pin an explicit approved patch or immutable image digest rather than rely on the latest tag.

## 3.2 Object Storage and Data Lake Integration

ClickHouse can query data directly from S3-compatible object storage and can ingest data from object storage into native tables. This supports a separation between durable lake storage and performance-optimized ClickHouse storage.

## 3.3 Distributed Coordination

ClickHouse Keeper is the ClickHouse-native coordination service used for replicated/distributed deployments. Production quorum design should use an odd number of Keeper members, with three members as the baseline for the initial HA design.

## 3.4 Portainer Operating Model

Portainer supports stack deployment from Git repositories as well as web-editor/upload methods. For enterprise governance, Git-backed stack definitions and CI-controlled promotion are preferred so that the deployed configuration remains traceable and reviewable.


# 4. Architecture Options Analysis

| **Option**                                                 | **Strengths**                                                                | **Risks / Limitations**                                                                        | **Recommendation**                                 |
|------------------------------------------------------------|------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|----------------------------------------------------|
| ClickHouse-only warehouse                                  | Simple runtime; excellent OLAP performance.                                  | Raw/history tightly coupled to one engine; weaker multi-engine reuse; backup/storage pressure. | Not preferred as the enterprise target.            |
| Object storage lake + ClickHouse marts                     | Durable raw lake, high-performance curated layer, clear hot/cold separation. | Requires ingestion/metadata discipline and two storage tiers.                                  | Recommended baseline.                              |
| Open table format first (Iceberg) + multiple query engines | Strong interoperability and future engine flexibility.                       | Higher operational/catalog complexity before multi-engine need is proven.                      | Evaluate in Phase 2+ only when justified.          |
| Kubernetes-native data platform from day one               | Strong orchestration and elastic patterns at scale.                          | Significantly higher skills/operations burden for current scope.                               | Defer until scale and SRE requirements justify it. |

# 5. Component Evaluation

| **Capability**      | **Initial Choice**                     | **Alternative / Future**          | **Decision Basis**                                                     |
|---------------------|----------------------------------------|-----------------------------------|------------------------------------------------------------------------|
| Analytical database | ClickHouse                             | Other OLAP engines if required    | High-throughput analytical queries and real-time serving.              |
| Durable lake        | S3-compatible object storage + Parquet | Iceberg tables/catalog            | Low-cost durable storage and engine independence.                      |
| Batch ingestion     | Airbyte and/or custom workers          | NiFi / other ELT tools            | Connector coverage vs custom control.                                  |
| CDC                 | Debezium                               | Native/vendor CDC tools           | Open event-based CDC pattern; introduce when real-time need is proven. |
| Streaming           | Kafka or Redpanda                      | Managed event platform            | High-throughput ingestion; Phase 9, not Phase 1.                       |
| Transformation      | dbt-clickhouse                         | Custom SQL / orchestration SQL    | Versioned transformation logic and testable models.                    |
| Orchestration       | Airflow or Dagster                     | Existing enterprise scheduler     | Adopt only when pipeline dependency management is required.            |
| Observability       | Prometheus + Grafana + Loki            | Enterprise monitoring integration | Matches repository baseline and supports operational signals.          |
| CI/CD               | GitHub + Jenkins + Harbor + Trivy      | Equivalent enterprise toolchain   | Traceable artifact promotion and security scanning.                    |

# 6. Data Architecture Research

A Medallion-style data model is recommended because it creates explicit contracts between ingestion, cleansing, business modeling, and serving. The physical implementation does not need to force every layer into ClickHouse; Landing/Bronze may remain in object storage while Silver/Gold/Serving are materialized into native ClickHouse tables where performance matters.

| **Layer**     | **Primary Role**                            | **Preferred Storage**               | **Key Controls**                                          |
|---------------|---------------------------------------------|-------------------------------------|-----------------------------------------------------------|
| Landing       | Immutable receipt of source extracts/events | Object storage                      | Original file preservation, checksums, ingestion metadata |
| Bronze / Raw  | Source-aligned normalized files/data        | Object storage / raw ClickHouse     | Schema capture, batch ID, source timestamps               |
| Core / Silver | Cleaned, deduplicated, conformed entities   | ClickHouse native tables            | Data quality checks, CDC version rules                    |
| Mart / Gold   | Business facts, dimensions, aggregates      | ClickHouse native tables            | Business definitions, reconciliation, performance design  |
| Serving       | Dashboard/API optimized datasets            | ClickHouse views/materialized views | SLA, query limits, RBAC                                   |
| Archive       | Cold long-term history                      | Object storage                      | Retention, legal hold, lifecycle policy                   |


# 7. Feasibility Assessment

| **Dimension**           | **Assessment**     | **Conditions**                                                                                     |
|-------------------------|--------------------|----------------------------------------------------------------------------------------------------|
| Technical feasibility   | High               | Benchmark with representative data/query mix before production sizing.                             |
| Operational feasibility | Medium-High        | Team must own Docker, ClickHouse operations, backup, monitoring, and incident runbooks.            |
| Security feasibility    | High with controls | TLS, RBAC, network segmentation, secret management, audit/change control required.                 |
| Scalability             | High               | Scale up first; add replication and shards based on measured bottlenecks.                          |
| Cost predictability     | Medium-High        | Object storage reduces long-term storage cost; hardware and concurrency still require measurement. |
| Future interoperability | High               | Durable lake can later support Iceberg and additional engines.                                     |

# 8. Principal Risks and Mitigations

| **Risk**                                      | **Impact** | **Mitigation**                                                                       | **Owner**       |
|-----------------------------------------------|------------|--------------------------------------------------------------------------------------|-----------------|
| Single-host topology mistaken for HA          | Critical   | Label DEV/UAT clearly; production replicas/Keeper on separate hosts/failure domains. | Platform        |
| Unbounded parts / poor MergeTree design       | High       | Benchmark partition/order keys; monitor active parts and merge backlog.              | Data/ClickHouse |
| Manual Portainer drift                        | High       | Git-backed stacks; CI/CD approvals; record emergency changes and reconcile to Git.   | DevOps          |
| Backup exists but restore unproven            | Critical   | Scheduled restore drills; measure actual RPO/RTO evidence.                           | SRE             |
| Sensitive data exposed through broad accounts | High       | Service accounts, least privilege, row policies, quotas, network restrictions.       | Security/Data   |
| Over-engineering before business value        | Medium     | Phase-gated adoption; defer Kafka/Iceberg/Kubernetes until justified.                | Architecture    |
| Sizing based on generic hardware tables       | High       | Performance benchmark using production-like data, concurrency, and SLOs.             | Platform/Data   |

# 9. Recommendation

1.  Approve a UAT baseline consisting of ClickHouse + S3-compatible object storage + Docker/Portainer + Prometheus/Grafana/Loki.

2.  Create the Landing/Bronze data lake contract and ClickHouse raw/core/mart/serving database conventions before onboarding many sources.

3.  Implement one representative source-to-dashboard vertical slice and benchmark ingestion, query latency, storage, and recovery.

4.  Define production SLO/RPO/RTO and security classification before committing production hardware.

5.  Deploy production HA only after the UAT benchmark and recovery test provide evidence for topology and sizing.

6.  Add CDC/streaming, Iceberg/catalog, and Kubernetes only when measurable requirements justify the operational complexity.

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
