# Implementation Plan - Phase 5: Open Lakehouse Formats, FinOps Governance, Data Contracts & Vector Search

แผนการดำเนินงานระยะที่ 5 (Phase 5) นี้ มุ่งเน้นการต่อยอดแพลตฟอร์มสู่ **Level 5 (Open Lakehouse)** และ **Level 6 (Intelligent Data Platform)** ตามกรอบ **DOC-06 (Modules, Capabilities & Future Enhancements)** และ **DOC-04 (Technical Design & Specifications)** โดยประกอบด้วย 4 โมดูลหลักระดับองค์กร:

1. **Module M03/M04: Lakehouse Open Format Interoperability (`sql/init/06_lakehouse_open_formats.sql`)**:
   - ตารางภายนอก (External Table) บน ClickHouse ด้วย `S3` Table Engine และ `Iceberg` Engine
   - รองรับการคิวรีไฟล์ Apache Parquet บน Object Storage (`landing/` และ `archive/`) ได้โดยตรงโดยไม่ต้องนำเข้าสู่ MergeTree ก่อน (Zero-ETL Ad-hoc Querying)
   - สคริปต์ส่งออกข้อมูลระยะยาว (Cold Archive Export) ไปยัง S3 Parquet

2. **Module M08: Data Contracts & Schema Evolution Guard (`contracts/`, `governance/validate_contract.py`)**:
   - การนิยาม Data Contract ตามมาตรฐานอุตสาหกรรมในรูปแบบ YAML ([`contracts/orders_contract.yml`](contracts/orders_contract.yml)) กำหนด Schema, Data Types, Nullability, Value Constraints และ SLA
   - โปรแกรมตรวจสอบความสอดคล้องของข้อมูลก่อนนำเข้า ([`governance/validate_contract.py`](governance/validate_contract.py)) ตรวจจับ Breaking Schema Changes (เช่น คอลัมน์หาย, ประเภทข้อมูลเปลี่ยน) และป้องกันข้อมูลผิดพลาดไม่ให้เข้าสู่ระบบ

3. **FinOps & Resource Quota Governor (`finops/query_cost_analyzer.py`)**:
   - ระบบวิเคราะห์ต้นทุนการประมวลผลและการใช้ทรัพยากร (FinOps & Cost Chargeback) โดยวิเคราะห์จาก ClickHouse `system.query_log`
   - คำนวณปริมาณข้อมูลที่อ่าน (Bytes Read), ปริมาณ Memory สูงสุด, ระยะเวลาประมวลผล, และประเมินต้นทุนต่อหน่วยงาน/ต่อบทบาทผู้ใช้งาน (`role_bi_readonly`, `role_api_service`, `role_etl_service`)
   - ตรวจจับคำสั่ง Query ที่ไม่มีประสิทธิภาพ (เช่น สแกนตารางโดยไม่ใช้ Partition Key หรือขาด ORDER BY filter)
   - จัดทำรายงาน FinOps อัตโนมัติใน [`docs/FINOPS_REPORT.md`](docs/FINOPS_REPORT.md)

4. **Module M12: Vector Embeddings & Semantic Search Demonstration (`ai_assistant/vector_search.py`)**:
   - สาธิตการใช้งานความสามารถ Vector Search บน ClickHouse ด้วยฟังก์ชันคำนวณระยะห่างทางคณิตศาสตร์ (`cosineDistance`, `L2Distance`) บนข้อมูล `Array(Float32)`
   - จัดทำคลังเวกเตอร์ความรู้สำหรับค้นหาเอกสารปฏิบัติการ (Runbook RAG Search) และแคตตาล็อกสินค้า ช่วยให้ AI Data Assistant ค้นหาบริบทได้อย่างแม่นยำ

5. **Developer & Operations CLI Integration**:
   - เพิ่มคำสั่ง `contract-validate`, `finops-report`, `vector-demo`, `lake-query` ลงใน `scripts/manage.ps1` และ `scripts/manage.sh`
   - อัปเดต `docs/DEVELOPER_GUIDE.md`, `docs/OPERATIONS_MANUAL.md`, และ `README.md`

---

## User Review Required

> [!IMPORTANT]
> **Data Contracts Enforcement**:
> การตรวจสอบ Data Contract จะทำหน้าที่เป็น Gatekeeper ระดับ Pre-Ingestion เพื่อป้องกันไม่ให้ข้อมูลต้นทางที่มีการเปลี่ยนโครงสร้างโดยไม่ได้ตกลงล่วงหน้า (Unannounced Schema Drift) ไหลเข้ามาสร้างความเสียหายแก่ตารางในชั้น Raw และ Silver

---

## Proposed Deliverables & Files

```text
Enterprise-Data-Lakehouse-Platform/
├── contracts/                                   # [NEW] Data Contracts Definition
│   └── orders_contract.yml                      # Open Data Contract Standard (ODCS) for Orders
│
├── governance/                                  # [NEW] Data Governance & Schema Guard
│   ├── __init__.py
│   └── validate_contract.py                     # Schema evolution & contract enforcement script
│
├── finops/                                      # [NEW] FinOps & Resource Governance
│   ├── __init__.py
│   └── query_cost_analyzer.py                   # ClickHouse query_log cost & memory analyzer
│
├── sql/init/
│   └── 06_lakehouse_open_formats.sql            # [NEW] S3 Parquet & Iceberg External Table Engines
│
├── ai_assistant/
│   └── vector_search.py                         # [NEW] ClickHouse Vector Cosine/L2 Distance Search Demo
│
├── scripts/
│   ├── manage.ps1                               # [MODIFY] Add contract-validate, finops-report, vector-demo
│   └── manage.sh                                # [MODIFY] Add contract-validate, finops-report, vector-demo
│
└── docs/
    ├── FINOPS_REPORT.md                         # [NEW] Generated Cost & Workload Chargeback Report
    ├── DEVELOPER_GUIDE.md                       # [MODIFY] Document Data Contracts & Vector Search
    └── OPERATIONS_MANUAL.md                     # [MODIFY] Document FinOps analysis & Contract Ops
```

---

## Verification Plan

### Automated Tests
1. **Python Compilation & Syntax**:
   - `python -m py_compile governance/*.py finops/*.py ai_assistant/*.py`
2. **Data Contract Validation**:
   - `python -m governance.validate_contract --contract contracts/orders_contract.yml` against valid & invalid payloads.
3. **FinOps Analyzer Execution**:
   - `python -m finops.query_cost_analyzer --dry-run` to generate cost chargeback breakdown and write `docs/FINOPS_REPORT.md`.
4. **Vector Semantic Search Demo**:
   - `python -m ai_assistant.vector_search --dry-run` to verify cosineDistance vector similarity computations.
5. **ClickHouse SQL Validation**:
   - Verify syntax of `sql/init/06_lakehouse_open_formats.sql`.
6. **CLI Integration Test**:
   - `.\scripts\manage.ps1 help` and dry-run invocations of all new commands.
