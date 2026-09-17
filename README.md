# Enterprise Data Lakehouse Platform

> **Production-Ready Lakehouse Platform with ClickHouse 26.8 LTS on Docker Engine & Portainer**
> Baseline: Ubuntu 24 LTS | S3 Lake Storage | dbt-clickhouse | Prometheus & Grafana | Governed by `AGENTS.md`

[![ClickHouse Version](https://img.shields.io/badge/ClickHouse-26.8%20LTS-yellow.svg)](https://clickhouse.com/)
[![OS Runtime](https://img.shields.io/badge/OS-Ubuntu%2024%20LTS-orange.svg)](https://ubuntu.com/)
[![Container Engine](https://img.shields.io/badge/Container-Docker%20%2B%20Portainer-blue.svg)](https://www.portainer.io/)
[![Governance](https://img.shields.io/badge/Governance-AGENTS.md-green.svg)](AGENTS.md)

---

## 1. Executive Summary / ภาพรวมระบบ

**Enterprise Data Lakehouse Platform** เป็นแพลตฟอร์มวิเคราะห์ข้อมูลระดับองค์กรที่ใช้สถาปัตยกรรม **Lakehouse + ClickHouse Acceleration**:
- **Object Storage (S3-Compatible)**: เป็นคลังจัดเก็บข้อมูลแบบเปิด (Open Storage) สำหรับจัดเก็บ Raw Data, Landing Files, และ Archive ระยะยาวด้วยฟอร์แมต **Apache Parquet**
- **ClickHouse 26.8 LTS**: ทำหน้าที่เป็น High-Performance OLAP Engine สำหรับประมวลผลข้อมูลระดับ Silver/Gold และให้บริการ Serving Layer ความเร็วระดับ Sub-second สำหรับ BI (Power BI), Dashboards, และ API
- **Portainer CE/EE**: สำหรับจัดการ Container Stacks และการติดตามสถานะการทำงานผ่าน Git-backed Stacks
- **dbt-clickhouse**: ควบคุมการแปลงข้อมูลตามสถาปัตยกรรมเหรียญรางวัล (Medallion Architecture)
- **Prometheus + Grafana + Loki**: ระบบ Observability สำหรับตรวจสอบสถานะและแจ้งเตือนตาม Runbook

### 📚 เอกสารและคู่มือการใช้งานระบบ (Key Documentation)
- 📘 **[คู่มือการพัฒนาระบบ (Developer Guide)](docs/DEVELOPER_GUIDE.md)**: สถาปัตยกรรม, การเขียน DDL, การพัฒนา dbt models, การต่อ Ingestion, และ AI Prompt Template
- 📕 **[คู่มือการติดตั้งและการใช้งานจริง (Operations & User Manual)](docs/OPERATIONS_MANUAL.md)**: การเตรียมเครื่อง, การติดตั้งบน Ubuntu 24 LTS, การบริหาร Portainer, การต่อ Power BI/DBeaver, และการกู้คืน DR
- 🧪 **[คู่มือ Deploy UAT Single Node](runbooks/01_portainer_git_stack_deployment.md)**: Portainer 4-stack deployment สำหรับ UAT
- 🏭 **[คู่มือ Deploy Production Multi-Host](runbooks/04_portainer_prod_deployment.md)**: Production readiness gates และ 3-failure-domain deployment
- 🧭 **[UAT Architecture Design](docs/architecture/UAT_ARCHITECTURE.md)**: Single-node topology, stacks, networks และ data flow
- 🏗️ **[Production Architecture Design](docs/architecture/PROD_ARCHITECTURE.md)**: Multi-host HA target architecture และ security zones
- 🗺️ **[พจนานุกรมข้อมูลและผังสายธารข้อมูล (Data Catalog & Lineage)](docs/DATA_CATALOG.md)**: Interactive Mermaid Data Lineage, Table Dictionary, SLA, PII Classification และ Retention
- 🏆 **[รายงานผลการทดสอบรับรองระบบระดับองค์กร (Enterprise Acceptance Test Report)](docs/ENTERPRISE_ACCEPTANCE_TEST_REPORT.md)**: ผลการทดสอบรับรองความสมบูรณ์ 12/12 โมดูล (100% Passed) ตามมาตรฐาน AGENTS.md
- 📗 **[กฎบัตรวิศวกรรมความปลอดภัย (AGENTS.md)](AGENTS.md)**: นโยบายการควบคุมความปลอดภัย Zero-Trust, Least Privilege และ Human Approval Gates


---

## 2. Logical Architecture / สถาปัตยกรรมเชิงตรรกะ

```text
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────────────────┐
│  Data Sources   │ ──> │   Ingestion Layer    │ ──> │   Object Storage (S3 Lake)  │
│ (DB, API, ERP)  │     │  (Batch/CDC/Workers) │     │  landing/ & bronze/ Parquet │
└─────────────────┘     └──────────────────────┘     └──────────────┬──────────────┘
                                                                    │
                                            ┌───────────────────────▼───────────────────────────┐
                                            │             ClickHouse 26.8 LTS Engine            │
                                            │  ┌───────────────┐        ┌────────────────────┐  │
                                            │  │ raw (Bronze)  │ ──dbt─>│   core (Silver)    │  │
                                            │  └───────────────┘        └─────────┬──────────┘  │
                                            │                                     │ dbt         │
                                            │  ┌────────────────────────┐         ▼             │
                                            │  │ serving (Pre-agg MVs)  │ <─── mart (Gold)      │
                                            │  └───────────┬────────────┘     (fact_sales)      │
                                            └──────────────┼────────────────────────────────────┘
                                                           │
                                        ┌──────────────────▼───────────────────┐
                                        │        Consumption & Analytics       │
                                        │  Power BI | Grafana | REST APIs | AI │
                                        └──────────────────────────────────────┘
```

---

## 3. Directory Structure / โครงสร้างโฟลเดอร์

```text
Enterprise-Data-Lakehouse-Platform/
├── AGENTS.md                                # Canonical Engineering & AI-governance policy
├── README.md                                # Master documentation
├── .env.example                             # Environment variable template (No secrets in Git)
│
├── agents/                                  # Multi-agent role definitions & handoff contracts
│   ├── orchestrator.md                      # A00 Delivery lead & gatekeeper
│   ├── solution-architect.md                # A01 Solution architecture & ADRs
│   ├── data-architect.md                    # A02 Medallion schemas & data contracts
│   ├── clickhouse-engineer.md               # A03 MergeTree, Keeper & query tuning
│   ├── data-pipeline-engineer.md            # A04 Ingestion, CDC & dbt models
│   ├── platform-devops.md                   # A05 Docker, Portainer & CI/CD
│   ├── security-governance.md               # A06 RBAC, network isolation & secrets
│   ├── sre-observability.md                 # A07 Prometheus, alerts, backup & DR
│   └── qa-validation.md                     # A08 Independent validation & testing
│
├── adr/                                     # Architecture Decision Records
│   ├── 0001-storage-separation-and-parquet.md
│   ├── 0002-clickhouse-medallion-layering.md
│   ├── 0003-docker-and-portainer-git-stacks.md
│   ├── 0004-clickhouse-keeper-coordination.md
│   └── 0005-dbt-clickhouse-transformation.md
│
├── compose/                                 # Docker Compose & Portainer Stacks
│   ├── docker-compose.dev.yml               # UAT Core: ClickHouse, MinIO, dbt, API
│   ├── docker-compose.datasources.yml       # UAT PostgreSQL/MySQL/SQL Server/MongoDB
│   ├── docker-compose.streaming.yml         # Redpanda & Console Streaming Stack (M02)
│   ├── docker-compose.prod-node1.yml        # PROD Node 1 (Replica 1 + Keeper 1)
│   ├── docker-compose.prod-node2.yml        # PROD Node 2 (Replica 2 + Keeper 2)
│   ├── docker-compose.prod-keeper3.yml      # PROD Node 3 (Keeper 3 quorum tie-breaker)
│   └── docker-compose.observability.yml     # Standalone Prometheus/Grafana/Loki stack
│
├── clickhouse/                              # ClickHouse Server Configurations
│   ├── config.d/                            # Storage tiering, keeper, clusters, prometheus, network
│   └── users.d/                             # Least-privilege roles, users & profiles
│
├── sql/init/                                # Database Initialization DDL
│   ├── 01_databases.sql                     # raw, core, mart, serving databases
│   ├── 02_medallion_tables.sql              # Bronze landing, Silver CDC, Gold fact_sales
│   ├── 03_materialized_views.sql            # AggregatingMergeTree & serving views
│   ├── 04_rbac_and_row_policies.sql         # Roles, Grants & Row-Level Security
│   └── 05_kafka_streaming.sql               # Kafka engine & streaming Materialized View
│
├── orchestration/                           # Pipeline Orchestration Module (M06)
│   ├── pipeline_orchestrator.py             # Master DAG runner with retries, audit & webhooks
│   └── airflow_dag.py                       # Production Airflow / Cloud Composer DAG
│
├── streaming/                               # Real-Time CDC & Streaming (M02)
│   └── kafka_producer_sim.py                # Synthetic real-time event generator for POS/eCommerce
│
├── dbt/                                     # dbt-clickhouse Transformation Project
│   ├── dbt_project.yml
│   ├── profiles.yml.example
│   ├── models/                              # Bronze, Silver, and Gold transformation models
│   └── tests/                               # Data quality integrity tests
│
├── data_quality/                            # Reconciliation & Scoring Engine (M05)
│   ├── reconciliation.py                    # Row counts & checksum reconciler
│   ├── anomaly_detector.py                  # Statistical Z-score & IQR anomaly detection (M05)
│   └── test_rules.py                        # Rule assertions and quality scoring
│
├── api/                                     # Governed Serving REST API Microservice (M07)
│   ├── Dockerfile
│   ├── main.py                              # FastAPI sub-second analytical endpoints
│   └── routers/                             # Sales and metrics routers
│
├── semantics/                               # Semantic Metrics Definitions (M12)
│   └── metrics.yml                          # Central enterprise KPI formulas
│
├── contracts/                               # Data Contracts Specification (M08)
│   └── orders_contract.yml                  # Open Data Contract Standard (ODCS) schema
│
├── governance/                              # Governance & Schema Guard (M08)
│   ├── validate_contract.py                 # Pre-ingestion schema drift & contract validator
│   └── policy_linter.py                     # AGENTS.md Policy-as-Code compliance linter
│
├── finops/                                  # FinOps & Resource Governance
│   └── query_cost_analyzer.py               # ClickHouse query_log cost & memory analyzer
│
├── ai_assistant/                            # Governed AI Assistant & Vector Search (M12)
│   ├── guardrails.py                        # Security filter (blocks DDL/DML, enforces LIMIT)
│   ├── text_to_sql.py                       # NL-to-SQL query assistant
│   ├── vector_search.py                     # Vector Cosine/L2 distance search demo
│   └── incident_triage.py                   # Automated ClickHouse incident triage & RCA
│
├── monitoring/                              # Observability & Alerting (M09)
│   ├── prometheus/alert_rules.yml           # Actionable alerts (latency, merges, keeper)
│   ├── grafana/dashboards/                  # ClickHouse Lakehouse Overview dashboard
│   └── loki/                                # Log aggregation
│
├── scripts/                                 # Developer CLI & Automation
│   ├── manage.sh                            # Linux/macOS unified developer CLI
│   ├── manage.ps1                           # Windows PowerShell unified developer CLI
│   ├── master_e2e_test.py                   # Master E2E 12-module acceptance test suite
│   ├── generate_catalog.py                  # Automated Data Catalog & Mermaid Lineage generator
│   ├── stress_test.py                       # Multi-threaded analytical concurrency benchmark
│   ├── smoke_test.py                        # Service health smoke test
│   ├── benchmark_queries.py                 # Query latency benchmark
│   ├── backup_clickhouse.sh                 # S3 backup script
│   └── restore_test.sh                      # Non-destructive restore drill
│
└── docs/                                    # Master Specifications & Manuals
    ├── DATA_CATALOG.md                      # พจนานุกรมข้อมูลและผังสายธารข้อมูล
    ├── FINOPS_REPORT.md                     # รายงานการวิเคราะห์ต้นทุน FinOps
    ├── ENTERPRISE_ACCEPTANCE_TEST_REPORT.md # ใบรับรองผลการทดสอบระบบระดับองค์กร (12/12 Passed)
    ├── DEVELOPER_GUIDE.md                   # คู่มือการพัฒนาระบบ
    ├── OPERATIONS_MANUAL.md                 # คู่มือการติดตั้งและการใช้งานจริง
    └── ...
```

---

## 4. Deployment Topologies / รูปแบบการติดตั้ง

### 4.1 DEV / UAT Single-Host (Evaluation & Benchmark)
> **หมายเหตุสำคัญ**: การรันทุก Container บน Host เดียวกันจัดเป็นสภาพแวดล้อมเพื่อการพัฒนาและทดสอบ Benchmark เท่านั้น **ไม่ใช่ระบบ High Availability (HA)**

UAT is deployed as four independently managed Portainer Git-backed stacks:

1. Core — ClickHouse, MinIO, dbt runner, and Serving API.
2. Data Sources — PostgreSQL, MySQL, SQL Server, and MongoDB.
3. Streaming — Redpanda and Redpanda Console.
4. Observability — Prometheus, Grafana, and Loki.

Deploy Core first because it owns the two shared Docker networks used by the
other stacks. See [the Portainer deployment runbook](runbooks/01_portainer_git_stack_deployment.md).

เริ่มใช้งานอย่างรวดเร็วด้วย **Developer CLI**:

```bash
# บน Linux / macOS:
./scripts/manage.sh start            # สตาร์ท DEV Stack
./scripts/manage.sh run-pipeline     # รัน Pipeline อัตโนมัติ (Ingest -> dbt -> Test -> Reconcile -> Backup)
./scripts/manage.sh contract-validate # ตรวจสอบข้อมูลเทียบกับ Data Contract
./scripts/manage.sh finops-report    # วิเคราะห์ต้นทุน Query และ Resource Quota
./scripts/manage.sh vector-demo      # ทดสอบ ClickHouse Vector Semantic Search
./scripts/manage.sh anomaly-detect   # ตรวจจับความผิดปกติของคุณภาพข้อมูลทางสถิติ (Z-score + IQR)
./scripts/manage.sh triage           # วินิจฉัยเหตุการณ์ผิดปกติและเชื่อมโยง Runbook อัตโนมัติ
./scripts/manage.sh policy-lint      # ตรวจสอบความสอดคล้องตามกฎบัตร AGENTS.md 100%
./scripts/manage.sh master-test      # รันการตรวจรับรองระบบครอบคลุมทั้ง 12 โมดูล
./scripts/manage.sh streaming-start  # เปิดระบบ Real-time Streaming (Redpanda + Console @ 8088)
./scripts/manage.sh stream-produce   # จำลองการยิงข้อมูลคำสั่งซื้อแบบ Real-time เข้า Kafka/ClickHouse
./scripts/manage.sh generate-catalog # อัปเดต Data Catalog และ Interactive Mermaid Lineage
./scripts/manage.sh stress-test 10   # ทดสอบโหลด 10 concurrent analytical users
./scripts/manage.sh smoke-test       # ตรวจสอบสุขภาพของทุก Service

# บน Windows PowerShell:
.\scripts\manage.ps1 start
.\scripts\manage.ps1 run-pipeline --dry-run
.\scripts\manage.ps1 contract-validate --dry-run
.\scripts\manage.ps1 finops-report --dry-run
.\scripts\manage.ps1 vector-demo "backup and restore drill"
.\scripts\manage.ps1 anomaly-detect --dry-run
.\scripts\manage.ps1 triage --simulate TOO_MANY_PARTS
.\scripts\manage.ps1 policy-lint
.\scripts\manage.ps1 master-test
.\scripts\manage.ps1 generate-catalog
.\scripts\manage.ps1 stress-test 10 --dry-run
.\scripts\manage.ps1 smoke-test
.\scripts\manage.ps1 benchmark
```

- **ClickHouse HTTP**: `http://localhost:18123/ping`
- **MinIO S3 API / Console**: `http://localhost:19090` / `http://localhost:19091`
- **RustFS S3 API / Console** (optional profile): `http://localhost:19094` / `http://localhost:19095`
- **Portainer UI**: `https://localhost:19443`
- **Grafana Dashboard**: `http://localhost:13000` (User: `admin`)

---

### 4.2 Production High Availability (HA) Topology
การติดตั้งสำหรับ Production จริงต้องแยก Container ข้าม **3 Physical Hosts / Failure Domains**:

```text
┌────────────────────────────────────────┐     ┌────────────────────────────────────────┐
│           PROD Host 01 (Node 1)        │     │           PROD Host 02 (Node 2)        │
│  - ClickHouse Server (Replica 1)       │     │  - ClickHouse Server (Replica 2)       │
│  - ClickHouse Keeper (Member 1)        │     │  - ClickHouse Keeper (Member 2)        │
│  - Portainer Agent                     │     │  - Portainer Agent                     │
└───────────────────┬────────────────────┘     └───────────────────┬────────────────────┘
                    │                                              │
                    │         ┌──────────────────────────┐         │
                    └────────>│   PROD Host 03 (Node 3)  │<────────┘
                              │  - Keeper (Member 3)     │
                              │  - Portainer Agent       │
                              └──────────────────────────┘
```

- **Host 01**: ใช้งาน [compose/docker-compose.prod-node1.yml](compose/docker-compose.prod-node1.yml)
- **Host 02**: ใช้งาน [compose/docker-compose.prod-node2.yml](compose/docker-compose.prod-node2.yml)
- **Host 03**: ใช้งาน [compose/docker-compose.prod-keeper3.yml](compose/docker-compose.prod-keeper3.yml)
- **การจัดการผ่าน Portainer**: ดูขั้นตอนการผูก Git-backed Stack ใน [runbooks/01_portainer_git_stack_deployment.md](runbooks/01_portainer_git_stack_deployment.md)

---

## 5. Medallion Data Architecture / สถาปัตยกรรมข้อมูล

ทุกตารางใน Bronze/Silver บังคับให้มีคอลัมน์ Technical Metadata ดังนี้:
1. `_source_system`: ระบบต้นทาง
2. `_source_table`: ตารางต้นทาง
3. `_ingested_at`: เวลาที่ข้อมูลถูกนำเข้าสู่ระบบ
4. `_source_updated_at`: เวลาที่ข้อมูลถูกแก้ไขที่ต้นทาง
5. `_batch_id`: รหัสรอบการนำเข้า (สำหรับ Replay/Audit)
6. `_record_hash`: Checksum เพื่อตรวจสอบการเปลี่ยนแปลง
7. `_is_deleted`: CDC Tombstone Flag

### ตัวอย่าง Fact Table พร้อม Hot/Cold Tiering ([sql/init/02_medallion_tables.sql](sql/init/02_medallion_tables.sql))
```sql
CREATE TABLE mart.fact_sales
(
    sale_date Date,
    sale_datetime DateTime64(3),
    order_id UInt64,
    customer_id UInt64,
    product_id UInt64,
    branch_id UInt32,
    quantity Decimal(18, 3),
    amount Decimal(18, 2),
    _source_system LowCardinality(String),
    _ingested_at DateTime64(3) DEFAULT now64(3)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(sale_date)
ORDER BY (sale_date, branch_id, product_id, customer_id)
TTL sale_date + INTERVAL 90 DAY TO VOLUME 'cold',
    sale_date + INTERVAL 7 YEAR DELETE
SETTINGS storage_policy = 'hot_to_cold';
```

---

## 6. Observability & Runbooks

- **Prometheus Metrics**: Scrape ClickHouse native metrics ที่ Port `9363` (QPS, Memory, Active Parts, Replication Queue)
- **Actionable Alerts**: กำหนดไว้ใน [monitoring/prometheus/alert_rules.yml](monitoring/prometheus/alert_rules.yml) โดยทุกลิงก์จะชี้ไปยัง Runbook สำหรับแก้ปัญหาโดยตรง:
  - Query Errors / Expensive Queries -> [runbooks/03_troubleshooting_and_failover.md#query-errors](runbooks/03_troubleshooting_and_failover.md)
  - Active Parts Explosion (>300 parts) -> [runbooks/03_troubleshooting_and_failover.md#parts-explosion](runbooks/03_troubleshooting_and_failover.md)
  - Replication Queue Lag -> [runbooks/03_troubleshooting_and_failover.md#replication-lag](runbooks/03_troubleshooting_and_failover.md)
  - Backup Overdue -> [runbooks/02_backup_and_restore_operations.md](runbooks/02_backup_and_restore_operations.md)

---

## 7. Disaster Recovery & Backup Drills

- **การสำรองข้อมูลอัตโนมัติ**: ใช้ [scripts/backup_clickhouse.sh](scripts/backup_clickhouse.sh) ยิงคำสั่ง Native `BACKUP` ไปยัง S3 Bucket โดยตรง
- **การซ้อมกู้คืนรายไตรมาส**: ใช้ [scripts/restore_test.sh](scripts/restore_test.sh) ในการกู้คืนแบบ Non-destructive ไปยัง Database ชั่วคราวเพื่อตรวจสอบความถูกต้องและจับเวลาจริงเปรียบเทียบกับเป้าหมาย RTO <= 4 ชั่วโมง

---

## 8. Governance & Security Policy

ทุกการเปลี่ยนแปลงต้องเป็นไปตาม **[AGENTS.md](AGENTS.md)**:
1. ห้าม Commit Production Secret ใดๆ ลงใน Git
2. ไม่อนุญาตให้ใช้ Single-Host อ้างสิทธิ์เป็น High Availability
3. การ Promote ขึ้น Production ต้องผ่านการทดสอบและได้รับความเห็นชอบจาก Human Approval Gate เสมอ
