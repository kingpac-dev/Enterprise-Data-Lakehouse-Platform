# ADR-0003: Docker Engine and Portainer Git Stacks over Kubernetes for Initial Platform

## Status
Accepted

## Context
Deploying an Enterprise Data Lakehouse on Kubernetes introduces substantial operational overhead (CSI storage drivers, complex stateful set management, network overlays, operator learning curves). The team requires an operationally simple, auditable, and reliable container runtime on Ubuntu 24 LTS that can be evaluated quickly in UAT and scaled cleanly to production HA.

## Decision
1. Standardize on **Docker Engine** with **Docker Compose V2** as the container runtime baseline.
2. Utilize **Portainer CE/EE** for operations, log inspection, and stack visibility.
3. Deploy stacks strictly via **Portainer Git-backed Stacks** linked to the Git repository, rather than manual, ad-hoc container creation in the Portainer UI.
4. Reserve Kubernetes/GitOps migration for future platform maturity phases if cluster density or multi-tenant microservices demand it.

## Consequences
### Positive
- Direct access to bare-metal / VM NVMe block performance without virtualization network overhead.
- Rapid developer onboarding, simple troubleshooting, and clear configuration traceability.
- Version-controlled infrastructure definitions in Git.

### Negative / Trade-offs
- Node orchestration across separate hosts in production HA requires separate Compose stacks per host or Docker Swarm / Portainer Edge agents.
- Automatic container rescheduling across physical hosts is not provided natively by plain Docker Compose (mitigated by ClickHouse application-level replication and Keeper).
