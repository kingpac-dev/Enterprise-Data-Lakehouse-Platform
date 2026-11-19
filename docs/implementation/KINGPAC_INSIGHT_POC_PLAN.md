# KingPac Enterprise Insight Platform — PoC และ Acceptance Plan

**สถานะ:** แผนเสนอจากรายงานที่ผู้ใช้ส่งวันที่ 19 พฤศจิกายน 2026; ระยะเวลาและเกณฑ์เป็นเป้าหมาย ไม่ใช่ผลทดสอบหรือ commitment

## 1. Traceability จากรายงาน

| ข้อเสนอ/ประเด็น | สถานะใน repository | งานที่ยังต้องพิสูจน์ |
|---|---|---|
| Superset + ClickHouse และ PostgreSQL/Redis | UAT Compose/image; local synthetic sandbox import และ chart-data API ผ่าน | ตรวจ browser และ deploy/connect บน UAT ขององค์กร |
| Grafana operational BI | Optional UAT image/provisioning override; plugin 4.14.0 และ datasource health ผ่านใน local sandbox | กำหนด read-only grants และทดสอบ connectivity/dashboard บน UAT ขององค์กร |
| Branch Row Policy / curated grants | มี [read-only audit tool](../../insight/check_branch_isolation.py) สำหรับสอง UAT accounts; ยังไม่มี policy ที่ enforce จริง | กำหนดเจ้าของข้อมูล/branch identities, สร้าง curated objects/policies, negative tests ผ่านทุก access path |
| AOV consistency | dbt formula ปรับเป็น revenue / distinct order ตาม catalog แบบ provisional; unit-test fixture ผ่านบน local ClickHouse sandbox | ตรวจ order identity/CDC/cancellation กับข้อมูลจริง และขอ Finance approval |
| API CORS | Default deny cross-origin, configurable explicit allowlist | ตั้ง origins ของ UAT จริงและทดสอบ consumer; CORS ไม่ใช่ authentication |
| Scheduling | ระบุ Celery worker/beat ใน target blueprint | ยังไม่ implement หรือทดสอบ SMTP/browser delivery, job isolation และ one-active-scheduler |
| Identity / SSO / MFA | ข้อกำหนดใน architecture | เลือก IdP และทดสอบ provisioning, deprovisioning, roles และ sessions |
| Metabase / Lightdash comparison | ระบุใน ADR | ยังไม่ได้ติดตั้งหรือเปรียบเทียบ usability, license, security หรือ cost |

## 2. Data correctness gates

- `gold_sales_summary` เดิมใช้ `avg(net_amount)` จึงเฉลี่ยต่อ line. สูตรใหม่ `sum(net_amount) / nullif(count(distinct order_id), 0)` แก้ความคลาดเคลื่อนกับ catalog สำหรับกลุ่มวัน/branch แต่ยังไม่ได้รับรองว่า `order_id` เป็น global key หรือเป็น completed order
- `silver_orders_cleaned` ใช้ `ReplacingMergeTree` และ sorting key `(order_date, branch_id, order_id)` โดยไม่มี line identifier/source. หาก order เดียวมีหลาย product lines การ merge หรือ `FINAL` อาจยุบหลายบรรทัดเข้าด้วยกัน; ต้องออกแบบ stable source line key และ tombstone/CDC semantics กับ Data Owner ก่อนใช้ KPI จริง. ห้ามแก้ `ORDER BY` แบบเดาโดยไม่มี migration และการทดสอบผลกระทบ
- `WHERE order_status != 'CANCELLED'` ยังรวม status อื่น เช่น PROCESSING/SHIPPED; `mart.fact_sales` ไม่มี status ให้ตรวจย้อนหลัง. Owner ต้องระบุรายการที่ถือเป็น completed/recognized, returns, currency และ deduplication
- AOV ที่ aggregate แล้วนำไปเฉลี่ยตรง ๆ ข้ามวัน/สาขาอาจผิด; คำนวณจาก numerator/denominator ที่ grain เดียวกัน และตรวจ distinct order ที่อาจอยู่ข้ามกลุ่ม
- dbt unit test `sales_aov_is_revenue_per_order_not_per_line` ผ่านบน local synthetic ClickHouse sandbox; ต้องรันซ้ำใน environment ที่อนุมัติและแนบ output. `dbt parse`/`dbt ls` เท่านั้นไม่ยืนยันว่า test หรือ model query ผ่าน

## 3. Business data products ที่ต้องมี owner

| Product | ตัวชี้วัดที่รายงานเสนอ | สถานะข้อมูล/owner |
|---|---|---|
| Executive Cockpit | Revenue, profit, cost, corporate KPI | Sources, owners, definitions และ thresholds `TBD` |
| Sales & Marketing | Sales trend, customer, product, forecast | UAT demo ใช้ `mart.fact_sales`; forecast และ certified metrics `TBD` |
| Production | OEE, yield, scrap, downtime | Machine/production events, calendar และ formulas `TBD` |
| Procurement | Spend, saving, supplier, PR → PO | Source mapping, currencies และ lifecycle `TBD` |
| Finance | Budget vs actual, margin, expenses | Ledger/budget source, accounting cutoff และ owner `TBD` |
| Quality | Defect rate, claim, complaint, CAPA | Denominators, ownership, lifecycle และ sources `TBD` |

สำหรับทุก product ต้องมี named owner/steward, grain, allowed dimensions, source, metric definition, refresh/freshness, classification, retention, access groups, reconciliation cases และ approval record. ห้ามสร้างตัวเลขตัวอย่างให้ดูเหมือนข้อมูลจริง

## 4. ลำดับงานเสนอ

| Phase | ระยะเวลาเป้าหมายจากรายงาน | Deliverable และ exit gate |
|---|---|---|
| 1 Architecture & gap analysis | สัปดาห์ 1 | ADR, data/security ownership, KPI contracts และ inventory ของ Power BI |
| 2 BI PoC | สัปดาห์ 2–3 | Superset + ClickHouse UAT; เก็บ usability/security comparison ของ Metabase/Lightdash ถ้าองค์กรอนุมัติ |
| 3 Business pilot | สัปดาห์ 4–5 | Sales, Production และ Executive pilots จากข้อมูลที่อนุมัติ; owner ตรวจตัวเลข |
| 4 Security/performance UAT | สัปดาห์ 6 | RBAC/RLS positive/negative, reconciliation และ workload tests พร้อมผลจริง |
| 5 Production readiness | สัปดาห์ 7–8 | Runbooks, SSO, HA, independent backup/restore, observability, scan และ sign-off |

ระยะเวลาสมมติว่ามีทีม Data Engineer/Software Engineer, access และตัวอย่างข้อมูลพร้อม; effort และวันเริ่มจริง `TBD`

## 5. เกณฑ์ทดสอบ PoC ที่เสนอ

| เกณฑ์ | Target จากรายงาน | วิธีเก็บหลักฐาน |
|---|---|---|
| Dashboard response P95 | ≤ 5 วินาที | จับเวลาจาก browser ตั้งแต่เปิด dashboard ถึง charts ที่กำหนด render เสร็จ; ระบุ dataset, filters, error rate, จำนวน samples, cold/warm cache และ query limits |
| Concurrent users | 20 | ใช้ 20 isolated user sessions ภายใต้ workload เดียวกัน; บันทึก resource sizing, test duration และผล P95/P50/errors |
| KPI reconciliation | 100% ของ approved test cases | Finance/Data Owner กำหนด source of truth, rounding/tolerance และ expected rows; ทดสอบหลาย lines/order, duplicates, cancellations, empty และ cross-period |
| Unauthorized access | 0 ในชุด negative cases ที่อนุมัติ | ทดสอบ branch/department ผ่าน ClickHouse, Superset datasets/chart/API/export/SQL Lab และ cache; กรณี network/auth error ห้ามนับเป็น deny ที่ผ่าน |

ต้องกำหนด sample size, test data volume, hardware, concurrent mix, refresh/cache policy, warm-up และ acceptance owner ก่อนเริ่ม. ไม่มี benchmark ที่รันหรือผ่านแล้วใน repo; ผลจาก UAT host เดียวใช้อนุมาน production HA ไม่ได้

### UAT isolation smoke test

จัดเตรียม synthetic `serving.v_daily_branch_sales` ให้มีทั้งสอง branch, ให้ผู้ดูแลยืนยันว่า raw/core/mart objects ที่ทดสอบมีอยู่ และสร้าง **สอง ClickHouse accounts** ที่แต่ละ account เห็นเฉพาะ branch ของตน พร้อมไม่มี `SELECT` บน `raw.orders_landing`, `core.dim_customer` และ `mart.fact_sales`. ผ่าน secret manager ให้ process ที่รันทดสอบรับ:

- `INSIGHT_TEST_CLICKHOUSE_URL` — UAT HTTP(S) endpoint ไม่มี credentials ใน URL
- `INSIGHT_TEST_BRANCH_A_USER`, `INSIGHT_TEST_BRANCH_A_PASSWORD`, `INSIGHT_TEST_BRANCH_A_ID`
- `INSIGHT_TEST_BRANCH_B_USER`, `INSIGHT_TEST_BRANCH_B_PASSWORD`, `INSIGHT_TEST_BRANCH_B_ID`

จาก repository root รัน `python insight/check_branch_isolation.py`. Script ทำเฉพาะ SELECT, ต้องเห็นข้อมูล fixture ของตน และถือว่า denied เฉพาะ ClickHouse access-denied code 497; connection/authentication failure ทำให้ test ล้มเหลว. ห้ามส่งรหัสผ่านเป็น command-line arguments หรือเก็บ output ที่มีข้อมูลจริง

การตรวจนี้เป็น **ตัวอย่างสอง accounts/tables เท่านั้น** ไม่ได้สร้าง policy, ทดสอบ writes, ทุก database object, dashboard, export, SQL Lab หรือ cache. Demo dataset ปัจจุบันอ่าน `mart.fact_sales` โดยตรง จึงต้องสร้าง curated dataset/connection ที่ตรงกับ policy ก่อนใช้ pilot แบบจำกัด branch; ห้ามถือว่า dashboard ตัวอย่างผ่าน RLS แล้ว

## 6. Power BI transition

ทำ inventory ของ reports, refresh schedules, consumers, security, DAX/Power Query, Excel, PBIX และ integrations; กำหนด owner และ migration disposition `rebuild / coexist / retain` โดย Data Owner. รัน parallel comparison บนช่วงเวลาและ filters เดียวกันก่อน cutover; อบรมผู้ใช้และมี rollback/communication plan. License reduction เป็น `TBD` จนแต่ละ workflow ผ่าน acceptance

## Handoff Contract

- **Scope & Sources Inspected:** รายงานผู้ใช้, repository dbt/SQL/API/observability, existing UAT candidate และ vendor docs
- **Assumptions & Decisions:** PoC ใช้ synthetic/masked data, Superset เป็น primary candidate; ระยะเวลาและเกณฑ์เป็นข้อเสนอ
- **Security & Operational Impact:** ต้องสร้าง curated permissions จริง; CORS ไม่ใช่ auth; audit tool ทำ SELECT เท่านั้นและไม่เปลี่ยน grants
- **Validation Commands & Results:** ดู [implementation status](KINGPAC_INSIGHT_IMPLEMENTATION_STATUS.md); มี local synthetic runtime evidence แต่ไม่มี RLS หรือ benchmark evidence
- **Remaining TBDs & Residual Risks:** Source-line identity, CDC, business KPI, six data-product owners, comparison tests, SSO/HA และ cost
- **Human Approval Required:** Data Owners/Finance, BI, Security, Platform และ CAB ตาม stage gates
