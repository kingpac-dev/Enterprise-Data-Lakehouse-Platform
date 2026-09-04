# Enterprise Data Lakehouse Project Master Plan

> Implementation, governance, delivery, milestone, and acceptance plan for the Enterprise Data Lakehouse Platform

**Document:** DOC-02 | Enterprise Data Lakehouse Platform

**Architecture & Planning Baseline | 2026-09-03**

*Status: Design baseline - organization-specific `TBD` values require human approval.*

> **Governance:** Repository `AGENTS.md` is the primary engineering and AI-governance policy. This document is a design baseline and must not be treated as evidence of production validation, security verification, HA testing, or recovery certification.

# Document Control

| **Item**          | **Value**                                                                                                                              |
|-------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| Document          | Project Master Plan                                                                                                                    |
| Purpose           | Define scope, phases, deliverables, governance, milestones, quality gates, risks, and acceptance criteria for implementation.          |
| Audience          | Project sponsor, steering committee, project manager, architecture, data engineering, DevOps, security, SRE, and business data owners. |
| Platform baseline | Ubuntu 24 LTS + Docker Engine + Portainer + ClickHouse 26.8 LTS branch                                                                 |
| Status            | Design baseline                                                                                                                        |
| Date              | 2026-09-03                                                                                                                             |
| Governance source | Repository `AGENTS.md` is the primary engineering and AI-governance policy.                                                              |

> **Control note:** technical values marked TBD are intentionally unresolved until workload, security, business continuity, and infrastructure requirements are formally approved.

# 1. Project Vision and Objectives

Build a secure, governed, observable, recoverable, and scalable enterprise analytical platform that centralizes durable data, accelerates BI and application analytics with ClickHouse, and creates a foundation for future real-time and AI-driven workloads.

- Create a governed enterprise data ingestion and storage foundation.

- Deliver high-performance analytical data marts and serving datasets.

- Reduce duplicated point-to-point reporting pipelines.

- Provide operational visibility, recovery capability, and controlled deployment.

- Enable phased evolution to CDC, streaming, open table formats, catalog/lineage, and AI/ML.

## Baseline Assumptions and Constraints

- Initial self-managed runtime uses Ubuntu 24 LTS, Docker Engine, Docker Compose, and Portainer.

- ClickHouse is the high-performance OLAP and curated serving engine; object storage remains the durable raw/long-term lake layer.

- DEV/UAT may begin as single-node for evaluation and benchmarking; this topology is not considered high availability.

- Production HA is designed around separate failure domains with ClickHouse replication and a three-member ClickHouse Keeper quorum.

- Git is the configuration source of truth; Jenkins/CI controls validation and promotion; Harbor is the target enterprise registry where available.

- Prometheus, Grafana, and Loki form the baseline observability stack.

- Organization-specific values that have not been approved are marked TBD rather than assumed.

# 2. Scope

| **In Scope**                                                                                                                                                                    | **Out of Initial Scope / Deferred**                                                                                                                                                                        |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Ubuntu/Docker/Portainer runtime; ClickHouse; object storage; batch ingestion; dbt models; BI serving; observability; security baseline; backup/restore; documentation/runbooks. | Kubernetes; full enterprise data catalog implementation; complex multi-region active-active; organization-wide MDM; unrestricted self-service ingestion; advanced streaming before use cases are approved. |

## 2.1 Primary Deliverables

- Architecture and system blueprint.

- Validated UAT stack and benchmark report.

- Data lake folder/bucket and metadata standards.

- ClickHouse database/schema/table conventions.

- CI/CD and Portainer Git Stack deployment process.

- Security/RBAC/network baseline.

- Prometheus/Grafana/Loki monitoring baseline.

- Backup, restore, and DR runbook.

- Production HA deployment plan.

- Source onboarding, transformation, and operational templates.

# 3. Delivery Roadmap


| **Phase**              | **Purpose**                     | **Key Deliverables**                                                                     | **Exit Gate**                                       |
|------------------------|---------------------------------|------------------------------------------------------------------------------------------|-----------------------------------------------------|
| 0 - Discovery          | Requirements and data inventory | Source inventory; volumes; SLAs; classification; business use cases; acceptance metrics. | Architecture inputs approved; TBD list established. |
| 1 - Core UAT           | ClickHouse + Portainer core     | Pinned ClickHouse image; volumes; health checks; initial users/RBAC; basic benchmark.    | Stable UAT runtime and repeatable deployment.       |
| 2 - Data Lake          | Durable object storage          | Landing/Bronze/Archive paths; lifecycle rules; credentials model; Parquet conventions.   | Write/read/recovery validation.                     |
| 3 - Batch Ingestion    | Onboard first sources           | Airbyte/custom worker; metadata columns; reconciliation; retry/idempotency.              | End-to-end source-to-raw pipeline.                  |
| 4 - Transformation     | Curated data models             | dbt project; raw/core/mart/serving models; tests; documentation.                         | Business reconciliation and model tests accepted.   |
| 5 - BI & Analytics     | Deliver business value          | Power BI/Grafana/API use case; query SLO measurements.                                   | User acceptance for first analytics product.        |
| 6 - Observability      | Operational visibility          | Metrics/logging dashboards; alert rules; operational KPIs.                               | Alert/runbook test completed.                       |
| 7 - Security Hardening | Production controls             | TLS, network segmentation, RBAC, secret handling, audit evidence.                        | Security review approved or risks accepted.         |
| 8 - Backup & DR        | Recoverability evidence         | Full/incremental backup; restore test; measured RPO/RTO.                                 | Restore drill demonstrated.                         |
| 9 - CDC/Streaming & HA | Scale and real-time             | Debezium/Kafka/Redpanda if needed; replicated ClickHouse; 3 Keeper nodes.                | Production benchmark, failover/recovery tests.      |

# 4. Work Breakdown Structure

| **Workstream**    | **Core Activities**                                            | **Owner Role**            |
|-------------------|----------------------------------------------------------------|---------------------------|
| Architecture      | ADR, logical/physical design, standards, NFRs, change impact   | Solution/Data Architect   |
| Infrastructure    | Hosts, storage, Docker, networks, certificates, firewall       | Platform Engineer         |
| ClickHouse        | Cluster/config/schema/engines/performance/replication          | ClickHouse Specialist     |
| Data Engineering  | Ingestion, CDC, data quality, orchestration, dbt               | Data Engineer             |
| Security          | Threat model, RBAC, secrets, logging, network controls         | Security Engineer         |
| DevOps            | Git/Jenkins/Harbor/Trivy, promotion, rollback, configuration   | DevOps Engineer           |
| Observability/SRE | SLIs/SLOs, metrics, alerts, capacity, backup/restore, runbooks | SRE                       |
| BI/Data Product   | Semantic rules, dashboards, reconciliation, UAT                | BI Engineer / Data Owner  |
| QA                | Test strategy, performance, recovery, regression evidence      | QA/Validation Engineer    |
| Governance        | Data ownership, retention, lineage requirements, approvals     | Data Governance / Sponsor |

# 5. Governance and Decision Model

| **Decision**                | **Proposer**               | **Required Review**         | **Approval / Gate**                                    |
|-----------------------------|----------------------------|-----------------------------|--------------------------------------------------------|
| Architecture change         | Architect                  | Security + Platform + Data  | Architecture authority / project sponsor as applicable |
| New data source             | Data Engineer / Data Owner | Security + Governance       | Data owner + project governance                        |
| Production release          | DevOps                     | QA + SRE + service owner    | Release approver (TBD)                                 |
| RBAC/privileged access      | Security / Platform        | Data owner                  | Authorized security approver                           |
| RPO/RTO/retention           | Business owner             | SRE + Security + Governance | Business sponsor                                       |
| Emergency production change | Operations                 | SRE/Security as applicable  | Change-control process; reconcile to Git afterward     |

# 6. Quality Gates and Acceptance Criteria

| **Gate**         | **Minimum Evidence**                                                                                             |
|------------------|------------------------------------------------------------------------------------------------------------------|
| Design Gate      | Approved architecture, risks, data classification, network flows, and unresolved TBDs visible.                   |
| Build Gate       | Compose/config syntax validated; no embedded secrets; pinned artifacts; health checks defined.                   |
| Data Gate        | Row-count/reconciliation checks; idempotency behavior; data quality tests; lineage metadata.                     |
| Performance Gate | Representative workload benchmark; query latency, throughput, CPU, memory, disk, parts/merge metrics recorded.   |
| Security Gate    | RBAC tested; privileged paths restricted; TLS/network controls verified; vulnerability findings triaged.         |
| Operations Gate  | Dashboards/alerts/runbooks ready; restore drill completed; deployment and rollback/recovery procedure exercised. |
| Production Gate  | Same approved artifact promoted; release approval recorded; smoke tests and post-deploy checks complete.         |

# 7. Project KPIs

| **KPI**                  | **Proposed Measure**                                             | **Target**                                     |
|--------------------------|------------------------------------------------------------------|------------------------------------------------|
| Deployment repeatability | Successful scripted/Git-based deployments vs manual-only changes | \>= 95% governed deployments; final target TBD |
| Data freshness           | Source-to-serving latency by dataset                             | Per dataset SLA - TBD                          |
| Query performance        | P95/P99 latency for agreed critical queries                      | TBD after benchmark                            |
| Data quality             | Critical checks passed / expected                                | \>= 99% or business-defined threshold          |
| Recovery readiness       | Successful scheduled restore tests                               | 100% scheduled drills completed                |
| Availability             | Serving layer availability                                       | TBD by business criticality                    |
| Security                 | Critical unresolved vulnerabilities at release                   | 0 unless explicitly approved exception         |
| Adoption                 | Priority dashboards/data products migrated                       | Phase target - TBD                             |

# 8. Schedule and Resource Planning

Calendar duration depends on source complexity, procurement, infrastructure readiness, and team allocation. The plan should be managed by phase gates rather than committing to dates that have not been validated.

| **Planning Item**              | **Status** |
|--------------------------------|------------|
| Project start                  | TBD        |
| Target UAT completion          | TBD        |
| Target production launch       | TBD        |
| Team allocation                | TBD        |
| Hardware procurement lead time | TBD        |
| Licensing / support model      | TBD        |
| Budget baseline                | TBD        |
| Production approver            | TBD        |

# 9. Project Risk Register

| **Risk**                                    | **Probability** | **Impact**  | **Response**                                                        |
|---------------------------------------------|-----------------|-------------|---------------------------------------------------------------------|
| Requirements/volume unknown                 | High            | High        | Complete Phase 0 inventory and benchmark before sizing.             |
| Skill gap in ClickHouse operations          | Medium          | High        | Training, runbooks, paired implementation, operational drills.      |
| Data ownership unclear                      | High            | Medium-High | Assign business/data owners per dataset before Gold model approval. |
| Scope expansion into streaming/AI too early | Medium          | Medium      | Phase gates and measurable business case required.                  |
| Manual production drift                     | Medium          | High        | Git source of truth, CI/CD controls, change audit.                  |
| Recovery assumptions untested               | Medium          | Critical    | Restore drill before production approval.                           |

# 10. Definition of Done for Initial Production Baseline

- Production topology and failure domains are documented and validated.

- No real secrets are committed in Git or examples.

- ClickHouse images/configuration are explicitly versioned.

- Approved ingestion sources are reconciled and monitored.

- Critical dashboards/API queries meet approved performance targets.

- Prometheus/Grafana/Loki or equivalent operational visibility is active.

- Backup and restore tests provide measured evidence.

- Runbooks cover deployment, incident handling, recovery, and access administration.

- Open risks/TBDs are either resolved or formally accepted by the responsible owner.

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
