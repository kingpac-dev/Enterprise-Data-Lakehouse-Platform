# ADR 0006: KingPac Enterprise Insight Platform

- **Status:** Proposed; รอ Architecture, Security, Data Owner และ Platform review
- **Date:** 2026-11-19
- **Decision owners:** BI Platform, Data Platform, Information Security, Business Data Owners; รายชื่อจริง `TBD`
- **Scope:** Self-hosted Enterprise BI บน Lakehouse ที่มีอยู่; UAT candidate ไม่ใช่ production approval

## Context

รายงานที่ผู้ใช้ส่งมาเสนอให้ลดการพึ่งพา Microsoft Power BI โดยใช้ ClickHouse, dbt, medallion data และ Grafana เดิม. Grafana ใน repository มีหน้าที่ observability เป็นหลัก; ฝ่ายธุรกิจต้องการ dashboards, self-service, drill-down, cross-filter และในอนาคต scheduled reports/exports โดยกำหนด ownership และสิทธิ์ให้ชัดเจน

การทดแทน Power BI ต้องตรวจ DAX, Power Query, PBIX, Excel, paginated reports, subscriptions และ semantic models เป็นราย workflow. ไม่มีหลักฐานใน repository ว่าระบบใหม่เทียบเท่าทุก workflow หรือผ่าน benchmark แล้ว

## Decision

1. ใช้ **Apache Superset เป็น primary BI candidate** สำหรับ PoC และ dashboard ธุรกิจ; ใช้ Grafana ต่อสำหรับ operational/observability use cases
2. ให้อ่านข้อมูลจาก ClickHouse `mart`/`serving` ผ่าน governed datasets/views และ read-only accounts. ไม่ต่อ BI เข้าฐานข้อมูลต้นทางหรือให้สิทธิ์ `raw`/`core` โดยปริยาย
3. ใช้ dbt/semantic catalog เป็นจุดตั้งต้นของ KPI contracts แต่ต้องตรวจ grain, source identity, CDC, formula, currency, timezone และ reconciliation ก่อนรับรองโดย Data Owner
4. ใช้ PostgreSQL เป็น Superset metadata store และ Redis สำหรับ cache; เพิ่ม Celery worker/beat, result backend และ browser rendering เมื่อ use case scheduled reports ได้รับอนุมัติและทดสอบ. UAT candidate ใน repo ยังไม่มีบริการ scheduling เหล่านี้
5. SSO/MFA, data isolation, TLS, audit, backup และ multi-host HA เป็นข้อกำหนดก่อน production. Shared ClickHouse user เพียงรายเดียวไม่สามารถสร้าง database-enforced per-person RLS โดยอัตโนมัติ
6. ใช้ Git-backed Portainer และ image ที่กำหนด version/digest; เส้นทาง production ต้องผ่าน GitHub → Jenkins → Harbor → Trivy → Portainer และ human gates ตาม AGENTS.md
7. ยังไม่สร้าง enterprise portal หรือ BI engine เองจนกว่า PoC, workflow inventory และ business acceptance แสดงว่าจำเป็น

## Alternatives and consequences

| ทางเลือก | ผลการตัดสินใจ |
|---|---|
| Superset | Primary PoC; ยืดหยุ่นด้าน SQL/dashboard แต่ต้องลงทุนด้าน operations, governance และ identity integration |
| Metabase | ตัวเปรียบเทียบเมื่อ usability ของผู้ไม่เขียน SQL เป็นประเด็น; ตรวจ edition, licensing และ security ตาม version ที่เลือกจริง |
| Lightdash | ตัวเปรียบเทียบสำหรับ dbt-centric metrics; ตรวจความสามารถ, edition และต้นทุน support จริง |
| Grafana only | เก็บไว้สำหรับ operations; ไม่สมมติว่าทดแทน workflow ทางธุรกิจทั้งหมด |
| สร้าง BI engine เอง | เลื่อนการตัดสินใจ; มีภาระ security, query tooling, visualization และ maintenance สูง |

Superset OSS ไม่มี license fee ต่อผู้ใช้สำหรับตัวซอฟต์แวร์ แต่ค่า infrastructure, engineering, support, patching และ recovery ยังเป็น `TBD`; ไม่ยกเลิก Power BI licenses จนผ่าน migration acceptance ของแต่ละ workflow

## Acceptance and review

ใช้ [PoC plan](../docs/implementation/KINGPAC_INSIGHT_POC_PLAN.md) และ [deployment blueprint](../docs/architecture/KINGPAC_INSIGHT_DEPLOYMENT_BLUEPRINT.md). เป้าหมายที่เสนอคือ dashboard response P95 ≤ 5 วินาที ที่ 20 concurrent users ภายใต้ workload ที่ระบุ, 100% ของ approved reconciliation cases ผ่าน และ unauthorized access 0 ครั้งในชุดทดสอบ. ทั้งหมดเป็นเป้าหมาย ไม่ใช่ผลที่วัดแล้ว

## Handoff Contract

- **Scope & Sources Inspected:** รายงานที่ผู้ใช้คัดลอก, AGENTS.md, Lakehouse SQL/dbt/Compose และ Apache Superset documentation
- **Assumptions & Decisions:** Superset เป็น primary candidate; Metabase/Lightdash ยังไม่ได้ PoC; Grafana คงไว้สำหรับ operations
- **Security & Operational Impact:** PostgreSQL/Redis และ application tier เพิ่มภาระ backup, hardening และ identity; branch isolation ยังต้อง implement และทดสอบ
- **Validation Commands & Results:** ADR เป็นข้อเสนอ ไม่ใช่หลักฐาน deployment, benchmark หรือ restore
- **Remaining TBDs & Residual Risks:** Data contracts, platform sizing, licenses/workflows, HA topology, SSO, isolation และ business KPI approval
- **Human Approval Required:** Architecture, BI/Data Owners, Platform, Security และ CAB ก่อน production promotion
