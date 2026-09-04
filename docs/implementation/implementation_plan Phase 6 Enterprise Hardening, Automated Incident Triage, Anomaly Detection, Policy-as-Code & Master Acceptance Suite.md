# Implementation Plan - Phase 6: Enterprise Hardening, Automated Incident Triage, Anomaly Detection, Policy-as-Code & Master Acceptance Suite

แผนการดำเนินงานระยะที่ 6 (Phase 6) นี้ มุ่งเน้นการยกระดับแพลตฟอร์มสู่ **Level 6: Intelligent Data Platform** อย่างสมบูรณ์แบบตามกรอบ **DOC-06 (Modules, Capabilities & Future Enhancements)** และ **DOC-02 (Project Master Plan)** โดยประกอบด้วย 4 โมดูลหลักสำหรับการนำไปใช้งานจริง (Production-Grade Readiness):

1. **Module M05/M08: Data Quality Anomaly Detection Service (`data_quality/anomaly_detector.py`)**:
   - ระบบตรวจจับความผิดปกติทางสถิติ (Statistical Z-score & IQR Anomaly Detection)
   - ตรวจจับความผิดปกติ 3 ด้านหลัก:
     - **Freshness Anomaly**: ข้อมูลล่าช้าเกินเกณฑ์ SLA (เช่น ไม่มีข้อมูลเข้าเกิน 60 นาที)
     - **Volume Anomaly**: ปริมาณข้อมูลผิดปกติอย่างมีนัยสำคัญ (เช่น ข้อมูลพุ่งสูงเกิน 3 เท่า หรือลดฮวบลงเป็น 0)
     - **Revenue / KPI Drift**: ยอดขายเฉลี่ยหรือยอดขายรวมเบี่ยงเบนจากค่าเฉลี่ยเคลื่อนที่ (Moving Average) เกิน 3 Standard Deviations
   - ส่งออกผลการวิเคราะห์เป็น Structured Alert JSON

2. **Module M09/M12: AI-Assisted Incident Triage Diagnostic (`ai_assistant/incident_triage.py`)**:
   - ระบบวิเคราะห์และวินิจฉัยปัญหาการทำงานของ ClickHouse อัตโนมัติ:
     - รองรับรหัสข้อผิดพลาดหลัก: `TOO_MANY_PARTS (Code 252)`, `TABLE_IS_READ_ONLY (Code 242)`, `MEMORY_LIMIT_EXCEEDED (Code 241)`, `SOCKET_TIMEOUT`, `REPLICATION_LAG`
     - **Zero-Trust Log Scrubbing**: กรองและลบข้อมูลความลับ รหัสผ่าน IP และข้อมูลส่วนบุคคลออกจาก Log ก่อนวิเคราะห์
     - จับคู่ Error Signature เข้ากับคู่มือปฏิบัติการ ([`runbooks/`](runbooks/)) และแนะนำขั้นตอนการแก้ไข (Root Cause & Step-by-Step Remediation Commands) แบบอัตโนมัติ

3. **Policy-as-Code & Governance Linter (`governance/policy_linter.py`)**:
   - ระบบตรวจสอบความสอดคล้องตามนโยบาย **[AGENTS.md](AGENTS.md)** แบบอัตโนมัติ:
     - Rule 1: Zero Hardcoded Secrets (สแกนตรวจจับ Credentials และ Private Keys)
     - Rule 2: Mandatory 7 Technical Ingestion Metadata Columns
     - Rule 3: Partition Key Low-Cardinality Enforcement (ห้ามใช้ Timestamp ละเอียดหรือ ID สูง)
     - Rule 4: Hot/Cold Storage Tiering Policy Check
     - Rule 5: Least-Privilege Role & Profile Boundaries

4. **Master End-to-End Acceptance Test Suite (`scripts/master_e2e_test.py`)**:
   - ชุดทดสอบความสมบูรณ์ทั้งระบบครอบคลุมทั้ง 12 โมดูล (M01 ถึง M12) แบบอัตโนมัติ:
     - ตรวจสอบ Ingestion, Streaming, dbt, Data Quality, API, Contracts, FinOps, Orchestrator, และ AI Assistant
   - ออกใบรับรองผลการทดสอบระบบระดับองค์กรใน [`docs/ENTERPRISE_ACCEPTANCE_TEST_REPORT.md`](docs/ENTERPRISE_ACCEPTANCE_TEST_REPORT.md)

5. **CLI & Documentation Updates**:
   - เพิ่มคำสั่ง `anomaly-detect`, `triage`, `policy-lint`, `master-test` ใน `scripts/manage.ps1` และ `scripts/manage.sh`
   - อัปเดต `docs/DEVELOPER_GUIDE.md`, `docs/OPERATIONS_MANUAL.md`, `README.md`, และ `walkthrough.md`

---

## User Review Required

> [!IMPORTANT]
> **Production Acceptance Gate**:
> การรัน Master End-to-End Test Suite จะทำหน้าที่เป็น Final Acceptance Gate ก่อนการ Deploy ขึ้นสภาพแวดล้อม Production เพื่อรับประกันว่าทุกโมดูลทำงานสอดประสานกัน 100% ตามข้อกำหนดใน [AGENTS.md](file:///c:/Users/supachai.nil/Documents/GitHub/Enterprise-Data-Lakehouse-Platform/AGENTS.md)

---

## Proposed Deliverables & Files

```text
Enterprise-Data-Lakehouse-Platform/
├── data_quality/
│   └── anomaly_detector.py                      # [NEW] Statistical Z-Score & IQR Anomaly Detection Service
│
├── ai_assistant/
│   └── incident_triage.py                       # [NEW] Automated Incident Diagnostic & Runbook Triage
│
├── governance/
│   └── policy_linter.py                         # [NEW] AGENTS.md Policy-as-Code Compliance Scanner
│
├── scripts/
│   ├── master_e2e_test.py                       # [NEW] Master E2E 12-Module Enterprise Acceptance Suite
│   ├── manage.ps1                               # [MODIFY] Add anomaly-detect, triage, policy-lint, master-test
│   └── manage.sh                                # [MODIFY] Add anomaly-detect, triage, policy-lint, master-test
│
└── docs/
    ├── ENTERPRISE_ACCEPTANCE_TEST_REPORT.md     # [NEW] Generated Master Acceptance Certification Report
    ├── DEVELOPER_GUIDE.md                       # [MODIFY] Document Anomaly Detection & Policy Linter
    └── OPERATIONS_MANUAL.md                     # [MODIFY] Document Incident Triage & Acceptance Procedures
```

---

## Verification Plan

### Automated Tests
1. **Python Compilation & Syntax**:
   - `python -m py_compile data_quality/anomaly_detector.py ai_assistant/incident_triage.py governance/policy_linter.py scripts/master_e2e_test.py`
2. **Anomaly Detector Validation**:
   - `python -m data_quality.anomaly_detector --dry-run` to test freshness, volume, and metric drift detection.
3. **Incident Triage Diagnostic Test**:
   - `python -m ai_assistant.incident_triage --simulate "TOO_MANY_PARTS"` and verify automated root cause + remediation command generation.
4. **Policy-as-Code Scanner Execution**:
   - `python -m governance.policy_linter` verifying 100% pass rate against AGENTS.md rules.
5. **Master E2E Acceptance Test Suite**:
   - `python scripts/master_e2e_test.py` verifying all 12 modules (M01-M12) and writing `docs/ENTERPRISE_ACCEPTANCE_TEST_REPORT.md`.
6. **CLI Integration Test**:
   - Test all new commands via `.\scripts\manage.ps1 help` and dry-run execution.
