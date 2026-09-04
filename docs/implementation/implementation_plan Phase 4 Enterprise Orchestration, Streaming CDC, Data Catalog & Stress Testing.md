# Implementation Plan - Phase 4: Enterprise Orchestration, Streaming CDC, Data Catalog & Stress Testing

แผนการดำเนินงานระยะที่ 4 (Phase 4) นี้ มุ่งเน้นการยกระดับแพลตฟอร์มสู่ **Level 4 (Near Real Time)**, **Level 5 (Open Lakehouse & Catalog)**, และ **Level 6 (Intelligent Data Platform)** ตามกรอบ **DOC-06 (Modules, Capabilities & Future Enhancements)** และ **DOC-02 (Project Master Plan)** โดยประกอบด้วย 4 โมดูลหลักระดับองค์กร:

1. **Module M06: Automated Pipeline Orchestrator (`orchestration/`)**:
   - Master Pipeline Orchestrator (`pipeline_orchestrator.py`) รองรับการรัน Pipeline แบบ End-to-End: Ingestion -> dbt Transformation -> Data Quality Reconciliation -> Snapshot/Backup -> Webhook Alerting
   - รองรับ State Tracking, Retry with Exponential Backoff, Execution Time Audit, และบันทึกประวัติ Run Log ลงระบบ
   - Template Apache Airflow / Cloud Composer DAG (`orchestration/airflow_dag.py`) สำหรับองค์กรที่ใช้ Enterprise Scheduler

2. **Module M02: Near Real-Time CDC & Streaming Ingestion (`streaming/`, `compose/docker-compose.streaming.yml`, `sql/init/05_kafka_streaming.sql`)**:
   - สถาปัตยกรรม Streaming ด้วย Redpanda (Kafka-compatible, ultra-low resource, single-binary ไร้ ZooKeeper)
   - ตาราง ClickHouse `Kafka` Table Engine และ Materialized View (`raw.mv_kafka_orders_to_landing`) ดึงข้อมูล JSON stream เข้าสู่ `raw.orders_landing` แบบ sub-second พร้อมแนบ 7 Technical Metadata อัตโนมัติ
   - โปรแกรมจำลองการส่ง Event สตรีมมิ่งความเร็วสูง (`streaming/kafka_producer_sim.py`) สำหรับทดสอบ Real-time POS/IoT transactions

3. **Module M08: Automated Enterprise Data Catalog & Lineage (`scripts/generate_catalog.py`, `docs/DATA_CATALOG.md`)**:
   - ระบบสร้าง Data Catalog และพจนานุกรมข้อมูล (Data Dictionary) อัตโนมัติจาก Schema และ Metadata ของ ClickHouse & dbt
   - ระบุ Classification ระดับความลับของข้อมูล (PII, CONFIDENTIAL, RESTRICTED, PUBLIC) และนโยบาย Retention/TTL
   - แผนภาพ Interactive Mermaid Data Lineage แสดงความสัมพันธ์ตั้งแต่ Source -> Raw -> Silver -> Gold -> Serving -> API/BI

4. **Module M09: Analytical Stress Testing & Concurrency Benchmark (`scripts/stress_test.py`)**:
   - เครื่องมือทดสอบโหลดและการใช้งานพร้อมกัน (Concurrent Analytical Users: 5-50 threads)
   - วัดผล Query Throughput (QPS), Latency Percentiles (P50, P90, P95, P99), Error Rate และ Memory Quotas ตามนโยบาย `AGENTS.md`

5. **CLI & Documentation Integration**:
   - เพิ่มคำสั่ง `run-pipeline`, `streaming-start`, `streaming-stop`, `stream-produce`, `generate-catalog`, `stress-test` ลงใน `scripts/manage.ps1` และ `scripts/manage.sh`
   - อัปเดต `docs/DEVELOPER_GUIDE.md` และ `docs/OPERATIONS_MANUAL.md`

---

## User Review Required

> [!IMPORTANT]
> **Resource Consumption & Network Isolation**:
> สแตก Streaming ใช้ Redpanda บนพอร์ต 9092 และ Redpanda Console บนพอร์ต 8088 โดยแยกเป็น Compose file อิสระ (`compose/docker-compose.streaming.yml`) เพื่อไม่ให้กระทบ DEV stack พื้นฐาน เว้นแต่จะเปิดใช้งานเมื่อต้องการทดสอบ Real-time streaming

---

## Proposed Deliverables & Files

```text
Enterprise-Data-Lakehouse-Platform/
├── orchestration/                                # [NEW] Enterprise Orchestration Module (M06)
│   ├── __init__.py
│   ├── pipeline_orchestrator.py                 # Master DAG Orchestrator with retries, stages & webhooks
│   └── airflow_dag.py                           # Production-ready Airflow DAG definition
│
├── streaming/                                    # [NEW] Real-Time CDC & Streaming (M02)
│   ├── __init__.py
│   ├── kafka_producer_sim.py                    # High-throughput event streamer for IoT/POS orders
│   └── requirements.txt                         # Streaming dependencies (kafka-python / redpanda)
│
├── compose/
│   └── docker-compose.streaming.yml             # [NEW] Redpanda + Console Streaming Compose Stack
│
├── sql/init/
│   └── 05_kafka_streaming.sql                   # [NEW] ClickHouse Kafka Engine & Ingestion MV
│
├── scripts/
│   ├── generate_catalog.py                      # [NEW] Automated Data Catalog & Mermaid Lineage Generator
│   ├── stress_test.py                           # [NEW] Multi-threaded Analytical Concurrency Benchmark
│   ├── manage.ps1                               # [MODIFY] Add run-pipeline, streaming-*, stress-test
│   └── manage.sh                                # [MODIFY] Add run-pipeline, streaming-*, stress-test
│
├── docs/
│   ├── DATA_CATALOG.md                          # [NEW] Generated Enterprise Data Catalog & Lineage
│   ├── DEVELOPER_GUIDE.md                       # [MODIFY] Document streaming & orchestration workflows
│   └── OPERATIONS_MANUAL.md                     # [MODIFY] Add streaming operations, catalog maintenance & SRE load test
```

---

## Verification Plan

### Automated Tests
1. **Python Compilation & Syntax**:
   - `python -m py_compile orchestration/*.py streaming/*.py scripts/*.py`
2. **Docker Compose Validation**:
   - `docker compose -f compose/docker-compose.streaming.yml config`
3. **Data Catalog Generation**:
   - `python scripts/generate_catalog.py --dry-run` to generate `docs/DATA_CATALOG.md` and verify valid Mermaid syntax.
4. **Orchestrator Dry-Run**:
   - `python -m orchestration.pipeline_orchestrator --dry-run` to verify task dependency graph and retry handling.
5. **Stress Test Dry-Run**:
   - `python scripts/stress_test.py --dry-run` to verify multi-threading logic and metric computations.
6. **CLI Integration Test**:
   - `.\scripts\manage.ps1 help` to ensure all new commands appear and resolve cleanly.
