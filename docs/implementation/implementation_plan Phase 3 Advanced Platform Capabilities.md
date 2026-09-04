# Implementation Plan - Phase 3: Advanced Platform Capabilities

แผนการดำเนินงานระยะที่ 3 นี้มุ่งเน้นการต่อยอดระบบตาม **DOC-06 (Modules, Capabilities & Future Enhancements)** และ **DOC-02 (Project Master Plan)** เพื่อยกระดับให้แพลตฟอร์มรองรับงานระดับ Enterprise ครบทุกมิติ:

1. **Modular Ingestion Framework (`ingestion/connectors/`)**:
   - สร้าง Base Ingestion Connector รองรับการดึงข้อมูลจากแหล่งต่างๆ: PostgreSQL, CSV/Parquet Drop files, และ REST APIs
   - ระบบจัดการ Watermark/State tracking บันทึก High-watermark อัตโนมัติ ป้องกันการดึงข้อมูลซ้ำซ้อน
   - การกักกันข้อมูลผิดพลาด (Error Quarantine) โดยไม่บันทึกความลับลง Log
2. **Data Quality & Reconciliation Engine (`data_quality/`)**:
   - ระบบตรวจสอบความสอดคล้องของข้อมูลแบบอัตโนมัติ (Source vs Raw vs Silver vs Gold Row Count & Checksum Reconciliation)
   - บันทึกประวัติและคะแนน Data Quality Score ลงตาราง `core.data_quality_history` เพื่อให้ทีม Audit และ SRE ตรวจสอบได้
3. **Governed Serving REST API (`api/`)**:
   - ไมโครเซอร์วิส FastAPI สำหรับให้บริการข้อมูลระดับ Serving Layer (`serving.v_daily_branch_sales` และ Gold Marts) แก่ระบบภายนอก
   - บังคับใช้สิทธิ์ `role_api_service`, Connection Pooling, Strict Query Timeout (<= 10s) และ OpenAPI Swagger documentation
4. **Governed Semantic Layer & AI Data Assistant (`ai_assistant/`)**:
   - Semantic Metrics Definition (`semantics/metrics.yml`) กำหนดสูตรคำนวณ KPI ทางธุรกิจที่เป็นมาตรฐานเดียวกันทั้งองค์กร
   - เครื่องมือ Text-to-SQL Assistant ที่มี Guardrails รัดกุม: บังคับ Read-only, บล็อกคำสั่ง DDL/DML, บังคับใส่ `LIMIT`, และจำกัดการเข้าถึงเฉพาะฐานข้อมูล `mart` และ `serving` เท่านั้น

---

## User Review Required

> [!IMPORTANT]
> **Governed Serving & AI Guardrails**:
> REST API และ AI Assistant จะทำงานภายใต้สิทธิ์ Least Privilege (`role_api_service` และ `role_bi_readonly`) และถูกจำกัดไม่ให้เข้าถึงข้อมูลชั้น `raw` หรือรันคำสั่งแก้ไขข้อมูลโดยเด็ดขาดตามนโยบาย [AGENTS.md](file:///c:/Users/supachai.nil/Documents/GitHub/Enterprise-Data-Lakehouse-Platform/AGENTS.md)

---

## Proposed Deliverables & Files

```text
Enterprise-Data-Lakehouse-Platform/
├── ingestion/connectors/                    # [NEW] Extensible Ingestion Framework
│   ├── __init__.py
│   ├── base_connector.py                    # Abstract connector with state tracking & metadata
│   ├── postgres_connector.py                # PostgreSQL / Relational DB CDC & batch connector
│   ├── file_drop_connector.py               # CSV/Parquet file landing watcher & loader
│   └── rest_api_connector.py                # Paginated REST API extractor
│
├── data_quality/                            # [NEW] Data Quality & Reconciliation
│   ├── __init__.py
│   ├── reconciliation.py                    # Automated row count, null check, and checksum reconciler
│   └── test_rules.py                        # Rule assertions and anomaly detection
│
├── api/                                     # [NEW] Governed Serving REST API
│   ├── Dockerfile                           # Container for FastAPI microservice
│   ├── requirements.txt
│   ├── main.py                              # FastAPI app with Swagger, CORS & health endpoints
│   └── routers/
│       ├── sales.py                         # Branch & daily sales endpoints (/api/v1/sales/*)
│       └── metrics.py                       # Data quality and platform metrics endpoints
│
├── semantics/                               # [NEW] Semantic Metrics Definition
│   └── metrics.yml                          # Central enterprise KPI formulas & descriptions
│
├── ai_assistant/                            # [NEW] Governed AI Query Assistant
│   ├── __init__.py
│   ├── guardrails.py                        # Strict SQL parser & validator (blocks DDL, enforces LIMIT)
│   └── text_to_sql.py                       # NL-to-SQL assistant consuming semantics & ClickHouse
│
├── compose/                                 # [MODIFY]
│   └── docker-compose.dev.yml               # Add optional 'api' serving container under profiles
│
├── scripts/                                 # [MODIFY]
│   ├── manage.sh                            # Add 'api-start', 'reconcile', 'ai-query' commands
│   └── manage.ps1                           # Add 'api-start', 'reconcile', 'ai-query' commands
│
└── docs/                                    # [MODIFY]
    ├── DEVELOPER_GUIDE.md                   # Document connector creation and semantic metrics
    └── OPERATIONS_MANUAL.md                 # Document REST API deployment and AI assistant operation
```

---

## Verification Plan

1. **Connector Framework Validation**: ทดสอบการทำงานของ `base_connector.py` และ `file_drop_connector.py`
2. **Reconciliation Execution**: รัน `reconciliation.py` เพื่อตรวจสอบยอดแถวระหว่าง Raw, Silver และ Gold
3. **REST API Smoke Test**: ทดสอบคอมไพล์และรัน Unit Check บน FastAPI endpoints
4. **AI Guardrails Validation**: ทดสอบการบล็อกคำสั่งอันตราย (เช่น `DROP TABLE`, `DELETE`, คำสั่งที่ไม่มี `LIMIT`)
5. **Docker Compose & Syntax Validation**: ตรวจสอบไวยากรณ์ Compose, XML, Python ทั้งหมด
