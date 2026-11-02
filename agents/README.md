# Project specialist roster and operating procedure

This directory contains the working briefs for specialist engineering assistants. `AGENTS.md` is authoritative if a brief differs from it. The design baseline and human ownership model remain in [DOC-07](../docs/07_Enterprise_Data_Lakehouse_AI_Agent_Team_and_Skills.md). Use the [production readiness worklist](../docs/PRODUCTION_READINESS_SPECIALIST_WORKLIST.md) to select evidence-backed work; an agent title does not imply a running service or a production approval.

| ID | Specialist brief | Owns | Independent challenge |
| --- | --- | --- | --- |
| A00 | [Orchestrator](orchestrator.md) | scope, sequence, risk and approval log | A08; human owner |
| A01 | [Solution architect](solution-architect.md) | topology, ADRs, NFRs | A05/A06/A07 as affected |
| A02 | [Data architect](data-architect.md) | medallion contracts, lineage, retention | A04/A08; data owner |
| A03 | [ClickHouse engineer](clickhouse-engineer.md) | DDL, replication, query design | A02/A08/A07 |
| A04 | [Pipeline engineer](data-pipeline-engineer.md) | ingestion, CDC, dbt, replay | A02/A08/A06 |
| A05 | [Platform/DevOps](platform-devops.md) | Compose, Portainer, CI/CD, images | A06/A07/A08 |
| A06 | [Security/governance](security-governance.md) | secrets, access, network, privacy | A08; security owner |
| A07 | [SRE/observability](sre-observability.md) | SLO, alerts, backup/DR | A08; operations owner |
| A08 | [QA/validation](qa-validation.md) | independent test evidence | domain owner distinct from author |
| A09 | [Documentation/ADR](documentation-adr.md) | manuals, diagrams, decision traceability | A08 and relevant domain owner |
| A10 | [BI/data product](bi-data-product.md) | KPI semantics, serving acceptance | A02/A08; data owner |
| A11 | [Capacity/FinOps](capacity-finops.md) | sizing, workload cost, benchmark | A03/A07/A08; budget owner |
| A12 | [API and AI application](api-ai-application.md) | API contracts, authorization, AI evaluation | A06/A08; product owner |

## Workflow for every change

1. A00 records the user outcome, affected environment, evidence source, owner, priority, measurable acceptance criterion and rollback constraint. Mark missing organizational values `TBD`.
2. The owning specialist inspects code/config and writes a scoped proposal or patch. Distinguish **implemented**, **documented**, **simulated**, and **verified in a running environment**.
3. An independent challenger inspects the diff and executes the relevant safe tests. Record the exact commands, results and limits. The author cannot certify their own production readiness.
4. A09 updates README/manual/runbook/ADR links when behavior or operating procedure changes. A00 tracks open risks in the worklist.
5. Human owners approve architecture, data access, security exceptions, destructive migrations, credential rotation and production promotion. Agents do not deploy to production.

Each handoff must include: **Scope & Sources Inspected; Assumptions & Decisions; Security & Operational Impact; Validation Commands & Results; Remaining TBDs & Residual Risks; Human Approval Required**. For Compose, SQL DDL or configuration changes, include syntax checks, backward compatibility, storage impact and rollback limits. Do not present static tests, Portainer stack entries or synthetic workloads as live health, HA or DR evidence.
