# Enterprise Data Lakehouse Platform with ClickHouse on Portainer.io Docker

## 1. Executive Summary

This document defines the architecture, planning, and design approach for an **Enterprise Data Lakehouse Platform** using **ClickHouse** as the analytics and serving engine, running on **Ubuntu 24 LTS**, **Docker Engine**, and **Portainer**.

The recommended approach is a **Lakehouse + ClickHouse Acceleration** model:

- **Object Storage** is the raw and long-term storage layer.
- **ClickHouse** is the OLAP, data mart, and serving engine for curated data.
- **Portainer** is used for controlled operations and stack visibility, not as an uncontrolled deployment path.
- The platform starts simple for UAT and grows to a replicated topology for production HA.

## 2. Guiding Principles

- Correctness
- Maintainability
- Testability
- Security
- Privacy
- Performance
- Observability
- Operational recoverability
- Least privilege
- Defense in depth
- Auditability
- Minimal and reviewable change sets

## 3. Target Platform Stack

### Infrastructure
- Ubuntu 24 LTS
- Docker Engine
- Portainer

### Data Lake
- S3-Compatible Object Storage
- Parquet
- Apache Iceberg (optional in Phase 2)

### Analytics
- ClickHouse 26.8 LTS
- MergeTree family engines
- Materialized Views
- Replication for production HA

### Ingestion
- Airbyte
- Debezium CDC
- Kafka / Redpanda
- Custom API Workers (.NET or Python)

### Transformation
- dbt-clickhouse
- Airflow / Dagster

### Consumption
- Power BI
- Grafana
- REST APIs
- Applications
- AI / ML / Notebooks
- Analysts

### Observability
- Prometheus
- Grafana
- Loki

### DevOps Governance
- GitHub
- Jenkins
- Harbor
- Trivy

## 4. Architecture Overview

```text
Data Sources
  -> Ingestion
  -> Object Storage Data Lake
  -> ClickHouse Analytics
  -> Transformation
  -> BI & AI Consumption
```

### Data Sources
- Databases
- ERP / Business Apps
- APIs
- Files
- IoT / Logs

### Ingestion
- Airbyte
- Debezium CDC
- Kafka / Redpanda
- API Workers

### Object Storage Data Lake
- Landing
- Bronze / Raw Parquet
- Archive

### ClickHouse Analytics
- raw
- core / silver
- mart / gold
- serving
- materialized views

### Transformation
- dbt-clickhouse
- Airflow / Dagster

### BI & AI Consumption
- Power BI
- Grafana
- Applications
- AI / ML
- Analysts

## 5. Key Architecture Decisions

1. Object Storage is the raw and long-term storage layer.
2. ClickHouse is the OLAP and serving engine for Silver / Gold.
3. Start with Docker + Portainer for operational simplicity.
4. Scale later to replicated ClickHouse for HA.

## 6. Data Architecture & Storage Strategy

### Medallion Layers
- **Landing**: immutable source files
- **Bronze / Raw**: source-aligned raw data
- **Core / Silver**: cleaned, normalized, deduplicated
- **Mart / Gold**: business facts, dimensions, aggregates
- **Serving**: dashboards, APIs, real-time analytics
- **Archive**: cold and historical storage

### Recommended ClickHouse Databases
- `raw`: ingested raw data, source-aligned
- `core`: cleansed and conformed core data
- `mart`: business marts, aggregates, dimensions
- `serving`: serving layer for dashboards and APIs

### Storage Strategy
- NVMe / SSD for hot MergeTree data
- S3-Compatible Object Storage for landing, archive, backup
- Parquet as the initial lake format
- Apache Iceberg optional in Phase 2

### Recommended Metadata Columns
- `_source_system`
- `_source_table`
- `_ingested_at`
- `_batch_id`
- `_record_hash`
- `_is_deleted`

## 7. ClickHouse Design Guidance

### Recommended Engines
- `MergeTree` for append-only fact/event tables
- `ReplicatedMergeTree` for production HA
- `ReplacingMergeTree` for CDC / versioned records
- `AggregatingMergeTree` for pre-aggregation
- `SummingMergeTree` for summation workloads
- `Distributed` for distributed query routing

### Example Fact Table Pattern

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

### Design Notes
- Avoid using very high-cardinality columns in `PARTITION BY`.
- Design `ORDER BY` around actual filtering and query patterns.
- Use materialized views for performance-critical serving datasets.

## 8. Deployment Topology & Portainer Operations

### UAT / Development – Single Node

Suitable for:
- evaluation
- proof of concept
- benchmark testing
- early integration

Typical stack on one host:
- Ubuntu 24 LTS
- Docker Engine
- Portainer
- ClickHouse
- S3-Compatible Object Storage
- Prometheus
- Grafana
- Loki

**Important:** This is **not true HA**.

### Production – Recommended High Availability Topology

```text
Host-01: ClickHouse Replica-01 + Keeper-01
Host-02: ClickHouse Replica-02 + Keeper-02
Host-03: Keeper-03
Shared:  S3-Compatible Object Storage
Clients: BI / API / Analysts
```

### Recommended Production Topology
- 1 Shard × 2 Replicas
- 3 Keeper Nodes
- Separate failure domains
- Internal-only admin access

### Governed Delivery & Operations Flow

```text
GitHub -> Jenkins -> Harbor -> Portainer Git Stack -> Docker Hosts
```

**Operational rule:** Use Portainer for controlled operations, not ad hoc unmanaged production changes.

## 9. Security, Observability & Disaster Recovery

### Security Controls
- RBAC
- Least Privilege
- TLS
- Network Segmentation
- Service Accounts
- Quotas
- Settings Profiles
- Row Policies

### Observability
Metrics and logs should provide visibility into:
- query rate
- error rate
- latency
- CPU
- memory
- disk
- replication health
- restart count

### Backup & DR
- `BACKUP / RESTORE`
- Incremental + Full Backup
- Off-site Copy Recommended
- Restore Test Quarterly
- `RPO = TBD`
- `RTO = TBD`

**Operational principle:** A backup is not reliable until restore testing is demonstrated.

## 10. Network Design

Recommended logical networks:
- `data_ingestion`
- `data_backend`
- `data_storage`
- `observability`
- `management`

### Network Guidance
- internal TLS
- least privilege
- firewall allow-listing
- network segmentation
- restricted inbound access
- controlled outbound access
- no unnecessary public exposure

### Sensitive Ports
Do not expose broadly:
- `9000` ClickHouse Native
- `9181` Keeper
- `9092` Kafka

Restrict `8123/8443` to trusted internal networks only.

## 11. Backup and Disaster Recovery Targets

The following are proposed and require formal business approval:

- **RPO**: TBD, proposed <= 1 hour
- **RTO**: TBD, proposed <= 4 hours
- **Incremental backup**: hourly
- **Full backup**: daily / weekly depending on dataset volume
- **Retention**: TBD
- **Restore test**: at least quarterly
- **Off-site copy**: recommended

## 12. Hardware Baseline (Starting Point Only)

### DEV
- 4–8 vCPU
- 16–32 GB RAM
- 500 GB SSD

### UAT
- 8–16 vCPU
- 32–64 GB RAM
- 1–2 TB NVMe

### PROD (per node)
- 16–32 vCPU
- 64–128 GB RAM
- 2–4+ TB NVMe

**Note:** Final sizing must be validated with actual workload benchmarks.

## 13. Implementation Roadmap

### Phase 0
- Requirements & Data Inventory

### Phase 1
- ClickHouse + Portainer Core

### Phase 2
- Object Storage

### Phase 3
- Batch Ingestion

### Phase 4
- dbt Transformations

### Phase 5
- BI & Analytics

### Phase 6
- Observability

### Phase 7
- Security Hardening

### Phase 8
- Backup & DR

### Phase 9
- CDC / Streaming & HA

## 14. Guiding Approach

- Start simple, benchmark early
- Build once, scale when justified
- Prefer governed and repeatable operations
- Add Iceberg and advanced engines only when needed

## 15. Expected Outcomes

- Fast Analytics
- Reliable Operations
- Future Expansion

## 16. Summary Recommendation

The recommended initial enterprise baseline is:

- ClickHouse 26.8 LTS
- S3-Compatible Object Storage
- dbt-clickhouse
- Prometheus / Grafana / Loki
- GitHub / Jenkins / Harbor / Trivy
- Docker + Portainer

This approach keeps the platform:
- simple enough to operate now
- scalable enough for future growth
- governed enough for enterprise use
- extensible enough for CDC, streaming, Iceberg, AI / ML, and distributed analytics later

## 17. Risks and Notes

- A multi-container deployment on a single host is not true HA.
- ClickHouse cluster HA requires separate hosts or failure domains.
- Storage and network bottlenecks may dominate performance before CPU does.
- Backup strategy is incomplete until restore testing is proven.
- RPO, RTO, retention, and data classification require business approval.

## 18. TBD Items

- Final source-system inventory
- Data classification by dataset
- Production host IPs / DNS names
- Final object storage product selection
- Final RPO / RTO
- Retention periods
- Capacity sizing after benchmark
- IAM / RBAC ownership model
- Change approval workflow
- BI semantic model ownership
