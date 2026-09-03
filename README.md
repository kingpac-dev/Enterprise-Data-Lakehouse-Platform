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
│   ├── docker-compose.dev.yml               # All-in-one DEV/UAT stack (Single-Host)
│   ├── docker-compose.prod-node1.yml        # PROD Node 1 (Replica 1 + Keeper 1)
│   ├── docker-compose.prod-node2.yml        # PROD Node 2 (Replica 2 + Keeper 2)
│   ├── docker-compose.prod-keeper3.yml      # PROD Node 3 (Keeper 3 quorum tie-breaker)
│   └── docker-compose.observability.yml     # Standalone Prometheus/Grafana/Loki stack
│
├── clickhouse/                              # ClickHouse Server Configurations
│   ├── config.d/
│   │   ├── storage_configuration.xml        # Hot NVMe + Cold S3 storage tiering
│   │   ├── keeper_config.xml                # ClickHouse Keeper 3-node Raft quorum
│   │   ├── clusters.xml                     # Distributed cluster definition
│   │   ├── prometheus.xml                   # Native Prometheus metric exporter (port 9363)
│   │   ├── network.xml                      # Network listen hosts & security
│   │   └── logging.xml                      # Structured JSON logs & query_log TTL
│   └── users.d/
│       ├── users.xml                        # User templates with password env injection
│       └── roles_and_profiles.xml           # Least-privilege roles, quotas & profiles
│
├── sql/init/                                # Database Initialization DDL
│   ├── 01_databases.sql                     # raw, core, mart, serving databases
│   ├── 02_medallion_tables.sql              # Bronze landing, Silver CDC, Gold fact_sales
│   ├── 03_materialized_views.sql            # AggregatingMergeTree & serving views
│   └── 04_rbac_and_row_policies.sql         # Roles, Grants & Row-Level Security
│
├── dbt/                                     # dbt-clickhouse Transformation Project
│   ├── dbt_project.yml
│   ├── profiles.yml.example
│   ├── models/
│   │   ├── bronze/sources.yml               # Raw source contract definitions
│   │   ├── silver/silver_orders_cleaned.sql # Cleaned & deduplicated CDC models
│   │   └── gold/gold_sales_summary.sql      # Aggregated daily sales summary
│   └── tests/
│       └── test_sales_amount_positive.sql   # Data quality integrity tests
│
├── monitoring/                              # Observability & Alerting
│   ├── prometheus/
│   │   ├── prometheus.yml                   # Scrape configs for ClickHouse, Keeper, MinIO
│   │   └── alert_rules.yml                  # Actionable alerts (latency, merges, keeper)
│   ├── grafana/
│   │   ├── provisioning/
│   │   └── dashboards/clickhouse_overview.json # Curated operational dashboard
│   └── loki/
│       └── loki-config.yml
│
├── runbooks/                                # Standard Operating Procedures
│   ├── 01_portainer_git_stack_deployment.md # Deploying stacks via Portainer Git
│   ├── 02_backup_and_restore_operations.md  # S3 Backup & Quarterly DR restore drill
│   └── 03_troubleshooting_and_failover.md   # Parts explosion, replication lag & failover
│
├── scripts/                                 # Operational Automation Scripts
│   ├── backup_clickhouse.sh                 # Native S3 backup script
│   ├── restore_test.sh                      # Automated non-destructive restore drill
│   └── validate_stack.sh                    # Compose & XML syntax validator
│
└── docs/                                    # Architectural Reports & Master Specifications
```

---

## 4. Deployment Topologies / รูปแบบการติดตั้ง

### 4.1 DEV / UAT Single-Host (Evaluation & Benchmark)
> **หมายเหตุสำคัญ**: การรันทุก Container บน Host เดียวกันจัดเป็นสภาพแวดล้อมเพื่อการพัฒนาและทดสอบ Benchmark เท่านั้น **ไม่ใช่ระบบ High Availability (HA)**

เริ่มใช้งานอย่างรวดเร็ว:
```bash
# 1. คัดลอกและตั้งค่า Environment Variables
cp .env.example .env

# 2. เริ่มการทำงานของ Stack DEV
docker compose -f compose/docker-compose.dev.yml up -d

# 3. ตรวจสอบสถานะ
docker compose -f compose/docker-compose.dev.yml ps
```

- **ClickHouse HTTP**: `http://localhost:8123/ping`
- **MinIO Console**: `http://localhost:9001` (User/Password ใน `.env`)
- **Portainer UI**: `https://localhost:9443`
- **Grafana Dashboard**: `http://localhost:3000` (User: `admin`)

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
