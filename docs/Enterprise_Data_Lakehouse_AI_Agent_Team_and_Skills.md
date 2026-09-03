# Enterprise Data Lakehouse AI Agent Team & Required Skills

> Human-Governed Multi-Agent Operating Model for Enterprise Data Lakehouse Engineering

**Document:** DOC-07 | Enterprise Data Lakehouse Platform

**Architecture & Planning Baseline | 2026-09-03**

*Status: Design baseline - organization-specific TBD values require human approval.*

> **Governance rule:** AI agents are engineering assistants, not autonomous production authorities. High-risk changes remain subject to explicit human review and approval.

# Document Control

| **Item**          | **Value**                                                                                                                    |
|-------------------|------------------------------------------------------------------------------------------------------------------------------|
| Document          | AI Agent Team Structure and Required Skills                                                                                  |
| Purpose           | Define the proposed AI agent roles, responsibilities, handoffs, skills, guardrails, review gates, and human ownership model. |
| Audience          | Engineering leadership, architecture, AI platform teams, software/data engineers, security, SRE, QA, and governance.         |
| Platform baseline | Ubuntu 24 LTS + Docker Engine + Portainer + ClickHouse 26.8 LTS branch                                                       |
| Status            | Design baseline                                                                                                              |
| Date              | 2026-09-03                                                                                                                   |
| Governance source | Repository AGENTS.md is the primary engineering and AI-governance policy.                                                    |

> **Control note:** Technical values marked `TBD` are intentionally unresolved until workload, security, business continuity, and infrastructure requirements are formally approved.

# 1. Operating Principle

AI agents are engineering assistants, not autonomous production authorities. They can inspect, analyze, draft, validate in safe environments, and prepare reviewable changes. Human owners remain accountable for architecture approval, sensitive access, production release, data governance, and destructive/recovery actions.

> **Separation of concerns:** The multi-agent model is designed for separation of concerns: one agent proposes, another validates from a different perspective, and high-risk actions require an explicit human gate.

# 2. Recommended AI Agent Team

| **Agent**                          | **Primary Mission**                                                                | **Typical Outputs**                                              |
|------------------------------------|------------------------------------------------------------------------------------|------------------------------------------------------------------|
| A00 Orchestrator / Delivery Lead   | Decompose work, enforce AGENTS.md workflow, coordinate agents, manage review gates | Task plan, dependency graph, consolidated status/TBD/risk report |
| A01 Enterprise Solution Architect  | Maintain overall architecture, boundaries, ADRs, NFRs                              | Architecture docs, ADRs, trade-off analysis                      |
| A02 Data Architect                 | Define domains, medallion contracts, schemas, ownership, metadata                  | Data model, contracts, naming/retention conventions              |
| A03 ClickHouse Specialist          | Optimize MergeTree design, replication, queries, performance                       | DDL, engine strategy, tuning/benchmark recommendations           |
| A04 Data Pipeline Engineer         | Design ingestion, CDC, orchestration, dbt and quality                              | Pipeline configs, dbt models/tests, replay/reconciliation design |
| A05 Platform / DevOps Engineer     | Docker/Compose, Portainer, Jenkins, Harbor, environments                           | Compose/config, pipeline templates, deployment/rollback runbooks |
| A06 Security & Governance Engineer | Threat model, RBAC, secrets, network/data controls                                 | Security review, role matrix, findings, required approvals       |
| A07 SRE / Observability Engineer   | SLI/SLO, monitoring, alerts, capacity, backup/DR                                   | Dashboards, alert rules, runbooks, recovery-test plans           |
| A08 QA / Validation Engineer       | Independent verification of configs, tests, data, performance                      | Test plans, validation evidence, acceptance report               |
| A09 Documentation / ADR Agent      | Maintain coherent documentation and decision traceability                          | README, runbooks, ADR index, cross-document consistency          |
| A10 BI / Data Product Analyst      | Translate business questions/KPIs into data product requirements                   | Metric definitions, UAT scenarios, serving requirements          |
| A11 Capacity / FinOps Analyst      | Analyze resource usage and growth; cost/performance trade-offs                     | Capacity model, benchmark analysis, cost scenarios               |

# 3. Agent Collaboration Flow

```text
Human Request / Backlog

|

v

A00 Orchestrator

|

+--> A01 Architecture --------+

+--> A02 Data Architecture ---+

+--> A03 ClickHouse ----------+----> Proposed Change Set

+--> A04 Pipelines -----------+ |

+--> A05 Platform/DevOps -----+ v

+--> A06 Security ----------- Review / Challenge

+--> A07 SRE ----------------+ |

+--> A08 QA <--------------- independent validation

+--> A09 Documentation ------+ |

+--> A10 Data Product -------+ v

`--> A11 Capacity/FinOps -----+----> HUMAN APPROVAL GATE

|

v

Controlled Implementation
```

# 4. Skills Matrix

| **Skill Area**       | **Required Knowledge**                                                                                          | **Primary Agents** |
|----------------------|-----------------------------------------------------------------------------------------------------------------|--------------------|
| ClickHouse           | MergeTree engines, partition/order keys, materialized views, system tables, replication, Keeper, backup, tuning | A03, A02, A07      |
| Data modeling        | Dimensional modeling, medallion, SCD/CDC, data contracts, metadata, quality                                     | A02, A04, A10      |
| Data engineering     | SQL, Python/.NET workers, Airbyte, Debezium, Kafka/Redpanda, Parquet, dbt                                       | A04, A02           |
| Containers/platform  | Linux, Docker, Compose, Portainer, storage mounts, networks, certificates                                       | A05, A07           |
| DevSecOps            | GitHub, Jenkins, Harbor, Trivy, SBOM, secret scanning, immutable promotion                                      | A05, A06, A08      |
| Security             | Threat modeling, IAM/RBAC, least privilege, TLS, network segmentation, logging/privacy                          | A06, A01           |
| SRE                  | SLIs/SLOs, Prometheus, Grafana, Loki, capacity, incident/recovery engineering                                   | A07, A11           |
| Testing              | Data reconciliation, dbt tests, integration, performance, failover/recovery tests                               | A08, A04, A07      |
| Governance           | Data ownership, classification, retention, lineage, approvals, ADRs                                             | A01, A02, A06, A09 |
| AI agent engineering | Prompt/context design, tool permissions, evaluation, guardrails, audit, human-in-loop                           | A00, A08, A06      |

# 5. Agent Responsibility Boundaries

| **Agent Category** | **May Do**                                                              | **Must Not Do Without Human Authorization**                           |
|--------------------|-------------------------------------------------------------------------|-----------------------------------------------------------------------|
| Design agents      | Analyze repository, draft architecture/DDL/config/docs, propose changes | Approve own high-risk architecture/security decisions as final        |
| Platform agents    | Generate/validate Compose/Jenkins configs in safe workspace             | Deploy to production, change firewall/credentials, delete volumes     |
| Data agents        | Draft pipelines/models/tests, run non-destructive validation            | Delete/overwrite production data, expose restricted datasets          |
| Security agent     | Review access paths and identify findings                               | Grant privileged access or accept security exceptions                 |
| SRE agent          | Draft alerts/runbooks and safe recovery tests                           | Trigger destructive production failover/restore without authorization |
| QA agent           | Run permitted tests and report evidence                                 | Falsify/assume test success or suppress failed evidence               |

# 6. Human Roles and Mandatory Gates

| **Human Role**              | **Accountability / Gate**                                                            |
|-----------------------------|--------------------------------------------------------------------------------------|
| Project / Business Sponsor  | Business priority, funding, approved RPO/RTO/availability, residual risk acceptance. |
| Architecture Owner          | Final material architecture decisions and ADR approval.                              |
| Data Owner                  | Dataset purpose, classification, access, retention, KPI semantics, UAT acceptance.   |
| Security Owner              | Privileged access, threat/risk acceptance, security exceptions.                      |
| Platform / Operations Owner | Runtime ownership, maintenance, incident response, capacity and recovery readiness.  |
| Release Approver            | Production promotion and emergency change authorization.                             |

# 7. Agent Handoff Contract

Every agent output should use the following structured handoff so another agent or human reviewer can validate it without reconstructing hidden assumptions:

- **Task:** 
- **Scope:** 
- **Inputs / Sources Inspected:** 
- **Assumptions:** 
- **Proposed Decision / Change:** 
- **Files or Artifacts Affected:** 
- **Security / Privacy Impact:** 
- **Data / Backward Compatibility Impact:** 
- **Operational / Recovery Impact:** 
- **Validation Performed (exact commands and results):** 
- **TBDs / Unknowns:** 
- **Residual Risks:** 
- **Human Approval Required:** 
- **Recommended Next Step:** 

# 8. Multi-Agent Review Patterns

| **Change Type**               | **Author Agent** | **Mandatory Challenger / Validator**                   |
|-------------------------------|------------------|--------------------------------------------------------|
| ClickHouse DDL/performance    | A03              | A02 + A08; A07 for production capacity impact          |
| Ingestion/CDC                 | A04              | A02 + A08 + A06 for sensitive data                     |
| Docker/Portainer/CI-CD        | A05              | A06 + A08 + A07                                        |
| RBAC/network/secrets          | A06              | A05 + human security owner                             |
| Backup/DR                     | A07              | A08 + human operations/business owner                  |
| Architecture change           | A01              | A02/A05/A06/A07 as affected + human architecture owner |
| Business metric/serving model | A10/A02          | Data owner + A08                                       |

# 9. AI Agent Evaluation Metrics

| **Metric**                     | **Meaning**                                                                                |
|--------------------------------|--------------------------------------------------------------------------------------------|
| Policy adherence               | Reads/uses AGENTS.md and does not bypass high-risk gates.                                  |
| Change precision               | Percentage of changes limited to requested scope without unrelated refactoring.            |
| Validation honesty             | Claims are backed by actual commands/results; failures remain visible.                     |
| Security hygiene               | No secret leakage, unsafe public exposure, or privilege escalation in generated artifacts. |
| Review defect rate             | Material defects found after agent claims readiness.                                       |
| Rollback/recovery completeness | Operational impact and rollback/recovery limitations documented.                           |
| Documentation consistency      | Architecture, technical spec, Compose, runbooks, and ADRs remain aligned.                  |
| Human acceptance               | Percentage of proposed changes approved with minimal rework.                               |

# 10. Suggested Repository Agent Structure

```text
repo/

|-- AGENTS.md # canonical engineering/governance policy

|-- agents/

| |-- orchestrator.md

| |-- solution-architect.md

| |-- data-architect.md

| |-- clickhouse-engineer.md

| |-- data-pipeline-engineer.md

| |-- platform-devops.md

| |-- security-governance.md

| |-- sre-observability.md

| |-- qa-validation.md

| `-- documentation-adr.md

|-- skills/

| |-- clickhouse/

| |-- data-onboarding/

| |-- deployment/

| |-- security-review/

| |-- backup-restore/

| `-- benchmark/

`-- docs/ ...
```

Platform-specific adapters should remain thin. The canonical policy belongs in AGENTS.md; agent files should describe role-specific workflows and outputs without silently weakening the root policy.

# 11. Required Agent Guardrails

- Production/external/destructive actions require explicit authorization.

- Credentials and sensitive data are never stored in prompts, memory, generated docs, or logs unnecessarily.

- Agents must inspect existing architecture and conventions before generating substantial changes.

- Agents must stop when high-risk assumptions are missing.

- Generated output is an untrusted draft until reviewed and validated.

- A separate validation agent should challenge high-impact changes.

- Evidence, unknowns, and residual risk remain visible in final handoffs.

# References

- ClickHouse 26.8 LTS release overview: <https://presentations.clickhouse.com/2026-release-26.8/>

- ClickHouse official packages / release channels: <https://packages.clickhouse.com/>

- ClickHouse documentation: <https://clickhouse.com/docs>

- ClickHouse Keeper: <https://clickhouse.com/clickhouse/keeper>

- ClickHouse Amazon S3 integration: <https://clickhouse.com/integrations/amazon_s3>

- ClickHouse integrations catalog: <https://clickhouse.com/integrations>

- Portainer: Add a new Docker stack / Git repository deployment: <https://docs.portainer.io/sts/user/docker/stacks/add>

- Portainer access control: <https://docs.portainer.io/advanced/access-control>

External references were reviewed for this document set on 2026-09-03. Product behavior and supported patch versions must be re-verified before production implementation.
