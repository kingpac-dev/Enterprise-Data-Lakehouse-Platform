# คู่มือการพัฒนาระบบ (Developer & Contributor Guide)
## Enterprise Data Lakehouse Platform

> **เอกสารคู่มือสำหรับ**: Data Engineers, ClickHouse Specialists, Platform Developers, และ AI Coding Agents  
> **เกณฑ์มาตรฐานระบบ**: Ubuntu 24 LTS | ClickHouse 26.8 LTS | Docker Compose V2 | dbt-clickhouse | ควบคุมโดย [AGENTS.md](../AGENTS.md)

---

## สารบัญ (Table of Contents)
1. [ภาพรวมสถาปัตยกรรมและหลักการวิศวกรรม (Architecture Principles)](#1-ภาพรวมสถาปัตยกรรมและหลักการวิศวกรรม)
2. [การเตรียมสภาพแวดล้อมเพื่อการพัฒนา (Local Development Setup)](#2-การเตรียมสภาพแวดล้อมเพื่อการพัฒนา)
3. [กฎการออกแบบฐานข้อมูลและ Schema ใน ClickHouse](#3-กฎการออกแบบฐานข้อมูลและ-schema-ใน-clickhouse)
4. [การพัฒนาโมเดลแปลงข้อมูลด้วย dbt-clickhouse](#4-การพัฒนาโมเดลแปลงข้อมูลด้วย-dbt-clickhouse)
5. [การสร้าง Data Ingestion Pipeline และการจัดการ Metadata](#5-การสร้าง-data-ingestion-pipeline-และการจัดการ-metadata)
6. [การทดสอบและการตรวจสอบคุณภาพโค้ด (Testing & Quality Assurance)](#6-การทดสอบและการตรวจสอบคุณภาพโค้ด)
7. [การทำงานร่วมกับ AI Agent Team และ Prompt Template](#7-การทำงานร่วมกับ-ai-agent-team-และ-prompt-template)
8. [Semantic Metrics Layer และ Governed AI Query Assistant](#8-semantic-metrics-layer-และ-governed-ai-query-assistant)
9. [Automated Pipeline Orchestration (Module M06)](#9-automated-pipeline-orchestration-module-m06)
10. [Real-Time CDC & Streaming Ingestion (Module M02)](#10-real-time-cdc--streaming-ingestion-module-m02)
11. [Enterprise Data Catalog & Data Lineage (Module M08)](#11-enterprise-data-catalog--data-lineage-module-m08)
12. [Concurrency Stress Testing & Benchmarks (Module M09)](#12-concurrency-stress-testing--benchmarks-module-m09)
13. [Data Contracts และ Schema Evolution Guard (Module M08)](#13-data-contracts-และ-schema-evolution-guard-module-m08)
14. [Lakehouse Open Formats: S3 Parquet & Apache Iceberg (Module M03/M04)](#14-lakehouse-open-formats-s3-parquet--apache-iceberg-module-m03m04)
15. [FinOps & Workload Resource Quota Governance](#15-finops--workload-resource-quota-governance)
16. [Vector Embeddings และ Semantic Search บน ClickHouse (Module M12)](#16-vector-embeddings-และ-semantic-search-บน-clickhouse-module-m12)
17. [การตรวจจับความผิดปกติของข้อมูลทางสถิติ (Statistical Anomaly Detection - M05)](#18-การตรวจจับความผิดปกติของข้อมูลทางสถิติ-statistical-anomaly-detection---m05)
18. [ระบบวินิจฉัยและแก้ปัญหาอัตโนมัติ (AI Incident Triage & Automated RCA - M09/M12)](#19-ระบบวินิจฉัยและแก้ปัญหาอัตโนมัติ-ai-incident-triage--automated-rca---m09m12)
19. [การตรวจสอบนโยบายทางวิศวกรรม (Policy-as-Code Linter - AGENTS.md Compliance)](#20-การตรวจสอบนโยบายทางวิศวกรรม-policy-as-code-linter---agentsmd-compliance)
20. [ชุดทดสอบรับรองระบบ 12 โมดูลแบบครอบคลุม (Master End-to-End Acceptance Suite)](#21-ชุดทดสอบรับรองระบบ-12-โมดูลแบบครอบคลุม-master-end-to-end-acceptance-suite)
21. [กระบวนการ Git Workflow และเกณฑ์การส่งมอบ (Definition of Done)](#22-กระบวนการ-git-workflow-และเกณฑ์การส่งมอบ)

---

## 1. ภาพรวมสถาปัตยกรรมและหลักการวิศวกรรม

แพลตฟอร์มนี้สร้างขึ้นตามรูปแบบ **Lakehouse + ClickHouse Acceleration** โดยมีหลักการสำคัญที่นักพัฒนาทุกคนต้องยึดถือ:
1. **แยก Storage ออกจาก Compute (Decoupled Architecture)**:
   - Object Storage (S3 / MinIO) จัดเก็บข้อมูลดิบ (Landing/Bronze) และประวัติย้อนหลังในรูปแบบ **Apache Parquet**
   - ClickHouse รับหน้าที่ประมวลผล OLAP สำหรับ Silver/Gold และ Serving Layer
2. **Medallion Architecture Separation**:
   - `raw`: เก็บข้อมูลดิบตามต้นทาง (Source-aligned, Append-only)
   - `core`: คลีนนิ่ง จัดมาตรฐาน ลบข้อมูลซ้ำ (Conformed Silver Layer)
   - `mart`: Business Facts & Dimensions ในรูปแบบ Star-Schema (Gold Layer)
   - `serving`: ตาราง AggregatingMergeTree และ Materialized Views สำหรับแดชบอร์ดความเร็วสูง
3. **Zero-Trust Secret Handling**:
   - ห้าม Hardcode รหัสผ่าน, API Keys, หรือ Connection Strings ลงในโค้ดหรือไฟล์ Git โดยเด็ดขาด ให้ใช้ `${VAR_NAME}` ผ่านไฟล์ `.env` เสมอ

---

## 2. การเตรียมสภาพแวดล้อมเพื่อการพัฒนา

### 2.1 สิ่งที่ต้องติดตั้งล่วงหน้า (Prerequisites)
- **Docker Engine** 24.0+ และ **Docker Compose V2** (หรือ Docker Desktop)
- **Python** 3.10+
- **Git**

### 2.2 การติดตั้งและเปิดใช้งานระบบจำลอง (DEV Stack)
```bash
# 1. Clone repository
git clone https://github.com/kingpac-dev/Enterprise-Data-Lakehouse-Platform.git
cd Enterprise-Data-Lakehouse-Platform

# 2. คัดลอก Environment File
cp .env.example .env

# 3. เริ่มการทำงานของ Stack การพัฒนา
# Linux / macOS:
./scripts/manage.sh start

# Windows PowerShell:
.\scripts\manage.ps1 start
```

### 2.3 การเข้าถึงเซอร์วิสต่างๆ (Default Endpoints)
| เซอร์วิส | URL | รหัสผ่านเริ่มต้น | หน้าที่ |
|---|---|---|---|
| **ClickHouse HTTP** | `http://localhost:18123` | ดูใน `.env` (`admin`) | ส่งคำสั่ง SQL ผ่าน Web/REST |
| **ClickHouse Native** | `localhost:19000` | ดูใน `.env` (`admin`) | เชื่อมต่อผ่าน DBeaver, dbt, CLI |
| **MinIO Console** | `http://localhost:19091` | ดูใน `.env` | ตรวจสอบไฟล์ Parquet ใน Lake |
| **Grafana** | `http://localhost:13000` | ดูใน `.env` (`admin`) | แดชบอร์ดตรวจสอบสุขภาพระบบ |
| **Prometheus** | `http://localhost:19093` | ไม่ต้องใช้ | เมทริกซ์และสถานะ Alert Rules |
| **Portainer** | `https://localhost:9443` | กำหนดเมื่อเปิดครั้งแรก | จัดการ Containers ผ่าน Web UI |

---

## 3. กฎการออกแบบฐานข้อมูลและ Schema ใน ClickHouse

ข้อกำหนดด้าน DDL ใน [AGENTS.md](../AGENTS.md) มีผลบังคับใช้กับการสร้างตารางทุกตารางในระบบ:

### 3.1 การเลือก Engine ของตาราง
- **`MergeTree`**: ใช้สำหรับตาราง Fact และ Event Log ที่เป็นแบบ Append-Only เช่น [sql/init/02_medallion_tables.sql](../sql/init/02_medallion_tables.sql)
- **`ReplacingMergeTree(_source_updated_at, _is_deleted)`**: ต้องใช้สำหรับตาราง CDC หรือมิติ (Dimension) ที่มีการแก้ไขข้อมูลจากต้นทาง เพื่อลบข้อมูลซ้ำตามเวลาอัปเดตล่าสุด
- **`AggregatingMergeTree`**: ใช้ใน Serving Layer สำหรับจัดเก็บผลลัพธ์คำนวณล่วงหน้า (State Functions) เช่น `sumState`, `uniqExactState`

### 3.2 กฎการออกแบบ PARTITION BY
> [!CAUTION]
> **ห้ามใช้ High-Cardinality Columns เป็น Partition Key**:
> ห้ามใช้ `UUID`, `order_id`, `customer_id`, หรือ Timestamp ที่ละเอียดระดับวินาทีใน `PARTITION BY` เพราะจะทำให้เกิด **Parts Explosion** จนระบบหน่วยความจำเต็ม
- ให้ใช้ระดับเดือนเป็นมาตรฐานเริ่มต้น: `PARTITION BY toYYYYMM(sale_date)`
- ตารางขนาดเล็กมาก (< 1 ล้านแถว) **ไม่จำเป็นต้องทำ Partition**

### 3.3 กฎการออกแบบ ORDER BY (Primary Sorting Key)
- เรียงลำดับคอลัมน์ตาม **รูปแบบการค้นหา (Query Access Pattern)** จากฟิลด์ที่มีความถี่ในการค้นหาและ Cardinality ต่ำไปยังสูง
- ตัวอย่างตาราง Fact ยอดขาย:
  ```sql
  ORDER BY (sale_date, branch_id, product_id, customer_id)
  ```

### 3.4 นโยบายจัดเก็บข้อมูลแบบ Hot/Cold Storage Tiering
- ตารางที่มีการเติบโตต่อเนื่องต้องกำหนดนโยบาย Tiering ในการย้ายข้อมูลเก่าลง Cold Volume (S3 Object Storage) อัตโนมัติ:
  ```sql
  TTL sale_date + INTERVAL 90 DAY TO VOLUME 'cold',
      sale_date + INTERVAL 7 YEAR DELETE
  SETTINGS storage_policy = 'hot_to_cold';
  ```

---

## 4. การพัฒนาโมเดลแปลงข้อมูลด้วย dbt-clickhouse

โครงการใช้ [dbt-clickhouse](../dbt/dbt_project.yml) เป็นมาตรฐานในการทำ Data Transformation

### 4.1 โครงสร้างโฟลเดอร์ dbt
```text
dbt/
├── dbt_project.yml          # การตั้งค่าโปรเจกต์
├── profiles.yml.example     # ตัวอย่าง Connection Profile
├── models/
│   ├── bronze/sources.yml   # การประกาศ Source Contracts จากตาราง raw
│   ├── silver/              # โมเดลคลีนนิ่ง ข้อมูลระดับ Conformed Entities
│   └── gold/                # โมเดลคำนวณยอดระดับ Business Marts
└── tests/                   # Data Quality Test Scripts
```

### 4.2 การสร้างโมเดล Silver (ตัวอย่าง: `silver_orders_cleaned.sql`)
```sql
{{ config(
    materialized='table',
    engine='ReplacingMergeTree(_source_updated_at, _is_deleted)',
    order_by=['order_date', 'branch_id', 'order_id'],
    partition_by='toYYYYMM(order_date)'
) }}

SELECT
    order_id,
    customer_id,
    toDate(order_timestamp) AS order_date,
    branch_id,
    product_id,
    round((quantity * unit_price) - discount, 2) AS net_amount,
    upper(status) AS order_status,
    _source_system,
    _source_table,
    _ingested_at,
    _source_updated_at,
    _batch_id,
    _record_hash,
    _is_deleted
FROM {{ source('bronze_raw', 'orders_landing') }}
WHERE _is_deleted = 0
```

### 4.3 การทดสอบและการรัน dbt
```bash
# รัน dbt ผ่าน Containerized Runner (ไม่ต้องลง dbt ในเครื่อง)
# Linux / macOS:
./scripts/manage.sh dbt-run
./scripts/manage.sh dbt-test

# Windows:
.\scripts\manage.ps1 dbt-run
.\scripts\manage.ps1 dbt-test
```

---

## 5. การสร้าง Data Ingestion Pipeline และการจัดการ Metadata

### 5.1 มาตรฐาน 7 คอลัมน์ Technical Metadata (บังคับใช้ทุกตาราง Raw)
ทุกแถวที่นำเข้าสู่ฐานข้อมูล `raw` จะต้องบันทึกคอลัมน์มาตรฐานดังต่อไปนี้:
1. `_source_system` (`LowCardinality(String)`): รหัสระบบต้นทาง เช่น `ERP_SAP`, `POS_BRANCH`
2. `_source_table` (`LowCardinality(String)`): ชื่อตารางต้นทาง เช่น `sales_orders`
3. `_ingested_at` (`DateTime64(3)`): เวลาที่บันทึกข้อมูลเข้าสู่ระบบ Lakehouse
4. `_source_updated_at` (`DateTime64(3)`): เวลาที่มีการเปลี่ยนแปลงที่ระบบต้นทาง
5. `_batch_id` (`String`): UUID ของรอบการนำเข้า (สำหรับ Audit & Replay)
6. `_record_hash` (`FixedString(32)`): Checksum MD5/SHA256 สำหรับตรวจจับการเปลี่ยนแปลงของแถว
7. `_is_deleted` (`UInt8`): ตัวบ่งชี้การลบ (0 = คงอยู่, 1 = ถูกลบ)

### 5.2 การทดสอบรัน Sample Ingestion Pipeline
เรามีสคริปต์ตัวอย่างใน [ingestion/sample_ingestion.py](../ingestion/sample_ingestion.py) ซึ่งสามารถรันเพื่อจำลองการนำเข้าข้อมูล:
```bash
# Linux / macOS:
./scripts/manage.sh ingest

# Windows:
.\scripts\manage.ps1 ingest
```

### 5.3 โครงสร้าง Modular Connector Framework (`ingestion/connectors/`)
โครงการมีเฟรมเวิร์กตัวเชื่อมต่อมาตรฐานพร้อมระบบติดตามสถานะ (State Watermarking) ใน [ingestion/connectors/](../ingestion/connectors):
- `BaseConnector`: คลาสแม่แบบที่มีระบบจัดการ Watermark, การแนบ Metadata 7 คอลัมน์, และการ Load เข้า ClickHouse
- `PostgresConnector`: ตัวดึงข้อมูลส่วนเพิ่มจาก PostgreSQL ผ่านคำสั่ง `WHERE updated_at > :watermark`
- `FileDropConnector`: ตัวดักจับและโหลดไฟล์ CSV/JSON ที่ส่งเข้ามายังโฟลเดอร์ Landing
- `RestApiConnector`: ตัวดึงข้อมูลผ่าน REST API พร้อมระบบแบ่งหน้า (Pagination) และ Rate Limiting อัตโนมัติ

---

## 6. การกระทบยอดข้อมูลและการตรวจสอบคุณภาพ (Data Quality & Reconciliation)

ระบบมี Engine สำหรับตรวจสอบความถูกต้องของข้อมูลแบบอัตโนมัติใน [data_quality/reconciliation.py](../data_quality/reconciliation.py):
- **Multi-layer Row Count Check**: เทียบจำนวนแถวระหว่าง Raw Landing -> Conformed Silver -> Mart Gold
- **Anomaly Detection**: ตรวจจับคีย์ธุรกิจที่เป็น NULL, ตรวจหายอดขายติดลบ, และตรวจหาวันที่เกินจริงในอนาคต
- **Data Quality Score (DQS)**: คำนวณคะแนนคุณภาพข้อมูล (0 - 100%) พร้อมบันทึกประวัติ

สั่งรันผ่าน Developer CLI:
```bash
# Linux / macOS:
./scripts/manage.sh reconcile

# Windows:
.\scripts\manage.ps1 reconcile
```


ก่อน Commit โค้ดหรือเปิด Pull Request นักพัฒนาต้องรันชุดตรวจสอบอัตโนมัติ:

```bash
# 1. ตรวจสอบความถูกต้องของ Compose และ XML Configs
# Linux / macOS:
./scripts/manage.sh validate

# Windows:
.\scripts\manage.ps1 validate

# 2. รัน Smoke Test เพื่อตรวจสุขภาพระบบ
# Linux / macOS:
./scripts/manage.sh smoke-test

# Windows:
.\scripts\manage.ps1 smoke-test

# 3. รัน Benchmark เพื่อวัดประสิทธิภาพ Query
# Linux / macOS:
./scripts/manage.sh benchmark

# Windows:
.\scripts\manage.ps1 benchmark
```

---

## 7. การทำงานร่วมกับ AI Agent Team และ Prompt Template

เมื่อต้องการให้ AI ช่วยพัฒนาฟีเจอร์ใหม่ ให้ปฏิบัติตาม **Prompt Engineering Standards** ใน [docs/AI_System_Design_and_Generation_Prompt_Template.md](AI_System_Design_and_Generation_Prompt_Template.md):
1. มอบหมายบทบาทตามความเชี่ยวชาญ (เช่น ให้ `clickhouse-engineer.md` ออกแบบ DDL, ให้ `security-governance.md` รีวิวสิทธิ์)
2. กำหนดตัวแปรระบบ (`<PROJECT_NAME>`, `<ENVIRONMENT>`, `<CLICKHOUSE_VERSION>`)
3. ปฏิบัติตาม **Agent Handoff Contract** เพื่อให้การส่งต่องานระหว่าง Agent และ Human Reviewer มีความชัดเจน โปร่งใส และตรวจสอบย้อนกลับได้เสมอ

---

## 8. Semantic Metrics Layer และ Governed AI Query Assistant

### 8.1 การนิยามตัวชี้วัดธุรกิจ (Semantic Metrics Catalog)
ไฟล์ [semantics/metrics.yml](../semantics/metrics.yml) เป็นจุดศูนย์รวมของสูตรคำนวณ KPI ระดับองค์กร (Single Source of Truth):
- นิยามชื่อเมทริกซ์ เช่น `net_revenue`, `total_orders`, `average_order_value`, `active_customers`
- ผูกสูตรคำนวณ SQL และตารางเป้าหมายในชั้น Mart/Serving ไว้อย่างชัดเจน ป้องกันการคำนวณคนละสูตรระหว่างทีม

### 8.2 การทดสอบใช้งาน Governed AI Assistant
ระบบมีผู้ช่วย AI ตอบคำถามภาษาธรรมชาติเป็น SQL ใน [ai_assistant/text_to_sql.py](../ai_assistant/text_to_sql.py) ที่ทำงานภายใต้ **Security Guardrails** ([ai_assistant/guardrails.py](../ai_assistant/guardrails.py)):
- บังคับใช้สิทธิ์ Read-only เท่านั้น (ห้ามมีคำสั่ง `DROP`, `DELETE`, `UPDATE`, `INSERT`, `SYSTEM`)
- จำกัดขอบเขตการเข้าถึงเฉพาะชั้น `mart` และ `serving`
- บังคับใส่คำสั่ง `LIMIT` อัตโนมัติเพื่อป้องกันหน่วยความจำล้น

ทดสอบรันผ่าน Developer CLI:
```bash
# Linux / macOS:
./scripts/manage.sh ai-query "แสดงยอดขายรายวัน 14 วันล่าสุด"

# Windows:
.\scripts\manage.ps1 ai-query "แสดงยอดขายรายวัน 14 วันล่าสุด"
```

---

## 9. Automated Pipeline Orchestration (Module M06)

ระบบมี Master Pipeline Orchestrator ใน [orchestration/pipeline_orchestrator.py](../orchestration/pipeline_orchestrator.py) สำหรับควบคุมวงจรชีวิตข้อมูลแบบ End-to-End ตั้งแต่ต้นน้ำถึงปลายน้ำ:

```text
[1. INGESTION] -> [2. TRANSFORMATION] -> [3. DATA_TESTS] -> [4. RECONCILIATION] -> [5. BACKUP] -> [6. NOTIFICATION]
```

### 9.1 ความสามารถหลักของ Orchestrator
- **Automatic Retries with Backoff**: รองรับการลองใหม่ตามจำนวนครั้งที่กำหนด พร้อมเว้นระยะเวลาหน่วงอัตโนมัติ
- **Critical vs Non-Critical Step Isolation**: หากขั้นตอนหลัก (Ingestion, Transformation) ล้มเหลวจะหยุดทำงานทันที แต่หากขั้นตอนรอง (Backup, Reconciliation) ล้มเหลวสามารถเลือกให้ดำเนินงานต่อได้
- **Audit Logging**: บันทึกประวัติการรัน สถานะ ระยะเวลา และ Error Message ลงใน `orchestration/runs/<run_id>.json`
- **Webhook Alerting**: ส่งสรุปผลการรันไปยัง Slack / Teams / Webhook อัตโนมัติ

### 9.2 การสั่งการผ่าน CLI
```bash
# รัน Pipeline ทั้งหมด
./scripts/manage.sh run-pipeline

# จำลองการรันแบบ Dry-run โดยไม่เรียกคำสั่งภายนอกจริง
./scripts/manage.sh run-pipeline --dry-run

# รันบน Windows PowerShell
.\scripts\manage.ps1 run-pipeline --dry-run
```

### 9.3 การประยุกต์ใช้กับ Enterprise Scheduler (Airflow / Dagster)
มี Template DAG สำหรับ Apache Airflow / Google Cloud Composer ใน [orchestration/airflow_dag.py](../orchestration/airflow_dag.py) พร้อมกำหนด SLA, Task dependencies และเจ้าของ Pipeline

---

## 10. Real-Time CDC & Streaming Ingestion (Module M02)

สถาปัตยกรรมการรับข้อมูลแบบ Real-Time และ Change Data Capture (CDC) ออกแบบด้วยเทคโนโลยี **Redpanda** (Kafka-compatible, ultra-low resource, C++ single binary ไร้ภาระ ZooKeeper):

```text
[Streaming Producers / IoT / POS]
               │
               ▼ (JSON Events @ 9092)
[Redpanda Topic: enterprise.orders.events]
               │
               ▼ (Sub-second pull)
[ClickHouse Kafka Engine: raw.kafka_orders_queue]
               │
               ▼ (Materialized View: raw.mv_kafka_orders_to_landing)
[raw.orders_landing (พร้อม 7 Technical Metadata Columns)]
```

### 10.1 การเปิดใช้งาน Streaming Stack
สแตกสตรีมมิ่งแยกไว้ใน [compose/docker-compose.streaming.yml](../compose/docker-compose.streaming.yml) เพื่อประหยัดทรัพยากร:
```bash
# เปิดใช้งาน Redpanda และ Redpanda Console (พอร์ต 8088)
./scripts/manage.sh streaming-start

# เข้าใช้งาน Web Console เพื่อดู Topic และ Message Stream แบบ Real-time:
# URL: http://localhost:18088

# ทดสอบรัน Event Producer จำลองการส่งข้อมูลคำสั่งซื้อแบบ Real-time:
./scripts/manage.sh stream-produce

# หยุดการทำงานสแตกสตรีมมิ่ง
./scripts/manage.sh streaming-stop
```

---

## 11. Automated Data Catalog & Lineage (Module M08)

ระบบมีเครื่องมือสร้างพจนานุกรมข้อมูล (Data Catalog) และผังสายธารข้อมูล (Data Lineage) แบบโต้ตอบได้อัตโนมัติใน [scripts/generate_catalog.py](../scripts/generate_catalog.py):

- **Data Classification**: จัดหมวดหมู่ความลับของข้อมูลอัตโนมัติ (เช่น `customer_name` เป็น `RESTRICTED (PII)`, `unit_price` เป็น `CONFIDENTIAL`)
- **Metadata Discovery**: ดึงข้อมูล Schema, Partition Key, Sorting Key, Retention Policy และ SLA จากนิยาม DDL ใน `sql/init/`
- **Interactive Mermaid Lineage**: สร้างแผนภาพ Mermaid ที่แสดงการเชื่อมโยงตั้งแต่ Sources -> Raw -> Silver -> Gold -> Serving -> Consumers

สร้าง Catalog ใหม่ได้ด้วยคำสั่ง:
```bash
# Linux / macOS:
./scripts/manage.sh generate-catalog

# Windows PowerShell:
.\scripts\manage.ps1 generate-catalog
```
ผลลัพธ์จะถูกบันทึกและแสดงผลที่ [docs/DATA_CATALOG.md](DATA_CATALOG.md)

---

## 12. Concurrency Stress Testing & Benchmarks (Module M09)

เพื่อทดสอบประสิทธิภาพและการรองรับโหลดพร้อมกันตามข้อกำหนด SLA ใน `AGENTS.md` ระบบมีเครื่องมือทดสอบโหลดใน [scripts/stress_test.py](../scripts/stress_test.py):

- จำลองการเข้าใช้งานพร้อมกันของผู้ใช้ BI และ API (5 ถึง 50 Threads พร้อมกัน)
- วัดค่า Throughput (QPS), อัตราความผิดพลาด (Error Rate) และการกระจายตัวของ Latency (P50, P90, P95, P99)
- ประเมินผลเทียบกับ Production SLA (เช่น P95 ต้องไม่เกิน 300 ms)

ทดสอบรันผ่าน CLI:
```bash
# ทดสอบโหลดที่ 10 concurrent threads:
./scripts/manage.sh stress-test 10

# บน Windows PowerShell (รองรับ --dry-run):
.\scripts\manage.ps1 stress-test 10 --dry-run
```

---

## 13. Data Contracts และ Schema Evolution Guard (Module M08)

เพื่อป้องกัน **Schema Drift** ที่ไม่แจ้งล่วงหน้าจากระบบต้นทาง แพลตฟอร์มใช้มาตรฐาน **Open Data Contract Standard (ODCS)** ในการทำสัญญาข้อมูลก่อนนำเข้าสู่ชั้น Bronze:

### 13.1 การนิยาม Data Contract
ไฟล์ [contracts/orders_contract.yml](../contracts/orders_contract.yml) กำหนด:
- เจ้าของข้อมูล (Data Owner) และช่องทางติดต่อ
- ข้อตกลงระดับการให้บริการ (SLA): ความสดของข้อมูล (Freshness), ความพร้อมใช้งาน (Availability $\ge$ 99.9%)
- ข้อกำหนดคอลัมน์: ประเภทข้อมูล, ห้ามเป็น NULL, ช่วงค่าที่ยอมรับได้ (เช่น `unit_price > 0`), และค่า Enumeration (`COMPLETED`, `PENDING`, `CANCELLED`)

### 13.2 การตรวจสอบก่อนนำเข้าข้อมูล (Pre-Ingestion Gate)
```bash
# ตรวจสอบความถูกต้องของข้อมูลเทียบกับ Data Contract
./scripts/manage.sh contract-validate

# บน Windows PowerShell:
.\scripts\manage.ps1 contract-validate --dry-run
```

---

## 14. Lakehouse Open Formats: S3 Parquet & Apache Iceberg (Module M03/M04)

ระบบรองรับการเชื่อมโยงข้อมูลแบบ **Open Lakehouse** ตามไฟล์ [sql/init/06_lakehouse_open_formats.sql](../sql/init/06_lakehouse_open_formats.sql):

- **External S3 Parquet Table (`raw.ext_s3_orders_landing`)**:
  เปิดให้ ClickHouse อ่านไฟล์ Parquet บน MinIO/S3 ได้โดยตรงผ่านฟังก์ชัน `S3()` ช่วยให้ทีมวิเคราะห์รัน Ad-hoc Query บนข้อมูลดิบได้ทันทีโดยไม่ต้องผ่านกระบวนการโหลด (Zero-ETL Querying)
- **Apache Iceberg Table (`raw.ext_iceberg_orders`)**:
  รองรับการเชื่อมต่อกับ Apache Iceberg Metadata Warehouse สำหรับงานที่ต้องการแชร์ตารางร่วมกับ Spark, Trino หรือ Databricks

---

## 15. FinOps & Workload Resource Quota Governance

เพื่อควบคุมค่าใช้จ่ายในการประมวลผลและการใช้หน่วยความจำ ระบบมีเครื่องมือวิเคราะห์ ClickHouse `system.query_log` ใน [finops/query_cost_analyzer.py](../finops/query_cost_analyzer.py):

- ติดตามและจำแนก Throughput, Bytes Read, Peak RAM, และประเมินต้นทุนต่อบทบาท (`role_bi_readonly`, `role_api_service`, `role_etl_service`)
- ชี้เป้าคำสั่งที่ไม่มีประสิทธิภาพ เช่น คำสั่ง Full Table Scan ที่ไม่ได้ใส่ Partition Key หรือลืมใส่ `LIMIT`
- จัดทำรายงานสรุปใน [docs/FINOPS_REPORT.md](FINOPS_REPORT.md)

เรียกดูรายงาน FinOps:
```bash
./scripts/manage.sh finops-report
# Windows:
.\scripts\manage.ps1 finops-report --dry-run
```

---

## 16. Vector Embeddings และ Semantic Search บน ClickHouse (Module M12)

ClickHouse 26.8 LTS รองรับการคำนวณเวกเตอร์หลายมิติด้วยฟังก์ชันเรขาคณิต `cosineDistance` และ `L2Distance` บนข้อมูลประเภท `Array(Float32)`:

ระบบมีตัวอย่างการค้นหาความหมาย (Semantic Search) ใน [ai_assistant/vector_search.py](../ai_assistant/vector_search.py) สำหรับค้นหาคู่มือปฏิบัติการ (Runbook Search) และบริบทการดูแลระบบ:
```bash
# ทดสอบค้นหาด้วยภาษาธรรมชาติ:
./scripts/manage.sh vector-demo "how to solve too many parts and replication lag"

# บน Windows PowerShell:
.\scripts\manage.ps1 vector-demo "backup and restore drill"
```

---

## 18. การตรวจจับความผิดปกติของข้อมูลทางสถิติ (Statistical Anomaly Detection - M05)

ระบบมีเซอร์วิสตรวจจับความผิดปกติของคุณภาพข้อมูลใน [data_quality/anomaly_detector.py](../data_quality/anomaly_detector.py) ซึ่งใช้โมเดลทางสถิติ (Z-Score และ Tukey's Interquartile Range - IQR) ในการประเมิน:
- **Freshness Latency**: ตรวจสอบเวลาห่างจากข้อมูลล่าสุด หากล่าช้าเกินเกณฑ์ SLA (เช่น > 60 นาที) จะแจ้งเตือนระดับ CRITICAL
- **Volume Anomalies**: ตรวจจับความผิดปกติของปริมาณข้อมูลในแต่ละแบตช์เทียบกับประวัติย้อนหลัง หากพบค่า Z-score เกิน $\pm 3.0$ หรืออยู่นอกช่วง IQR (Volume Drop / Volume Spike) จะหยุดท่อส่งข้อมูลทันที
- **Revenue / KPI Drift**: ตรวจสอบการเบี่ยงเบนของตัวเลขธุรกิจสำคัญ เช่น ยอดขายรวมต่อวัน หากเบี่ยงเบนเกิน $2.5\sigma$ จากค่าเฉลี่ยประวัติศาสตร์

```bash
# รันการตรวจสอบความผิดปกติทางสถิติ:
./scripts/manage.sh anomaly-detect

# จำลองการทดสอบตรวจจับความผิดปกติบน Windows:
.\scripts\manage.ps1 anomaly-detect --dry-run
```

---

## 19. ระบบวินิจฉัยและแก้ปัญหาอัตโนมัติ (AI Incident Triage & Automated RCA - M09/M12)

เมื่อเกิดปัญหาหรือข้อผิดพลาดใน ClickHouse คลัสเตอร์ เครื่องมือ [ai_assistant/incident_triage.py](../ai_assistant/incident_triage.py) จะทำการ:
1. **Zero-Trust Log Scrubbing**: กรองรหัสผ่าน IP addresses และ Token ออกจาก Log อัตโนมัติ เพื่อความปลอดภัยสูงสุด
2. **Error Signature Recognition**: ตรวจจับรหัสข้อผิดพลาด เช่น `TOO_MANY_PARTS (252)`, `TABLE_IS_READ_ONLY (242)`, `MEMORY_LIMIT_EXCEEDED (241)`, `REPLICATION_LAG`
3. **Runbook Linking & Remediation**: จับคู่ข้อผิดพลาดเข้ากับ Runbook ใน `runbooks/` พร้อมแนะนำคำสั่งบรรเทาและแก้ไขปัญหาทีละขั้นตอน (Step-by-step)

```bash
# ทดสอบจำลองวินิจฉัยปัญหา Too Many Parts:
./scripts/manage.sh triage --simulate TOO_MANY_PARTS

# บน Windows PowerShell:
.\scripts\manage.ps1 triage --simulate TOO_MANY_PARTS
```

---

## 20. การตรวจสอบนโยบายทางวิศวกรรม (Policy-as-Code Linter - AGENTS.md Compliance)

เพื่อรับประกันว่าโค้ดและคอนฟิกูเรชันทั้งหมดใน Repository สอดคล้องตามกฎบัตรความปลอดภัยและสถาปัตยกรรมใน [AGENTS.md](../AGENTS.md) 100% ระบบมี Policy Linter ใน [governance/policy_linter.py](../governance/policy_linter.py):
- **RULE-01 (Zero-Trust Secret)**: สแกนไฟล์ Compose, SQL, Python เพื่อป้องกันการ Hardcode รหัสผ่านหรือกุญแจลับ
- **RULE-02 (Mandatory Metadata)**: ตรวจสอบตาราง Bronze/Silver ว่ามี Technical Metadata ครบทั้ง 7 คอลัมน์
- **RULE-03 (Partition Key Rules)**: ตรวจสอบ DDL ว่าใช้ `toYYYYMM()` ไม่ใช้ High-cardinality columns ใน `PARTITION BY`
- **RULE-04 (Storage Tiering)**: ตรวจสอบ `storage_configuration.xml` ว่ามีทั้ง Hot NVMe และ Cold S3 Volume
- **RULE-05 (Least-Privilege Roles)**: ตรวจสอบว่ามีการกำหนด Role และ Memory Quota ชัดเจน

```bash
# รันการตรวจ Policy-as-Code:
./scripts/manage.sh policy-lint

# บน Windows PowerShell:
.\scripts\manage.ps1 policy-lint
```

---

## 21. ชุดทดสอบรับรองระบบ 12 โมดูลแบบครอบคลุม (Master End-to-End Acceptance Suite)

ก่อนการส่งมอบหรือ Release ขึ้น Production แพลตฟอร์มมีชุดทดสอบรับรองคุณภาพทั้ง 12 โมดูลใน [scripts/master_e2e_test.py](../scripts/master_e2e_test.py) ซึ่งจะทำการทดสอบตั้งแต่ M01 ถึง M12 พร้อมออกใบรับรองใน [docs/ENTERPRISE_ACCEPTANCE_TEST_REPORT.md](ENTERPRISE_ACCEPTANCE_TEST_REPORT.md):

```bash
# รันชุดทดสอบรับรองระบบทั้งหมด:
./scripts/manage.sh master-test

# บน Windows PowerShell:
.\scripts\manage.ps1 master-test
```

---

## 22. กระบวนการ Git Workflow และเกณฑ์การส่งมอบ

### 22.1 Branching Strategy
- `main`: กิ่ง Production ที่ผ่านการทดสอบและ Release Gate แล้วเท่านั้น
- `develop`: กิ่ง Integration หลักสำหรับการพัฒนา
- `feature/<name>`: กิ่งสำหรับการพัฒนาฟังก์ชันย่อย

### 22.2 Definition of Done (DoD) สำหรับแต่ละ Pull Request
- [ ] ไวยากรณ์ Docker Compose V2 ผ่านการตรวจสอบ (`docker compose config`)
- [ ] ไฟล์ XML และ SQL ทั้งหมดผ่านการตรวจสอบไวยากรณ์
- [ ] ปราศจากความลับหรือรหัสผ่านจริงที่ Hardcode ในโค้ด (ผ่าน `policy-lint` RULE-01)
- [ ] มีการกำหนด Technical Metadata ครบทั้ง 7 คอลัมน์สำหรับตารางนำเข้าข้อมูล (`policy-lint` RULE-02)
- [ ] มี dbt model และโมเดลเทสต์ที่เกี่ยวข้อง
- [ ] ผ่านการตรวจสอบ Data Contract (`contract-validate`)
- [ ] ผ่านการตรวจสอบความสอดคล้องนโยบายองค์กร 100% (`policy-lint`)
- [ ] ผ่านการทดสอบ Master Acceptance Suite 12/12 โมดูล (`master-test`)
- [ ] อัปเดตเอกสารประกอบ, Data Catalog และ ADR หากมีการเปลี่ยนแปลงสถาปัตยกรรม

