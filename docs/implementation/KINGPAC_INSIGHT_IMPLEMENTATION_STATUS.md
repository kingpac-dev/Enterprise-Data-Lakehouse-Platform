# KingPac Enterprise Insight Platform — Implementation Status

**วันที่บันทึก:** 19 พฤศจิกายน 2026 · **สถานะ:** ทดสอบ local synthetic sandbox แล้ว; ยังไม่ได้ deploy UAT ขององค์กรและยังไม่พร้อม production

## สิ่งที่เพิ่มใน repository

- [Solution Architecture และ migration plan](../architecture/KINGPAC_ENTERPRISE_INSIGHT_PLATFORM.md) ครอบคลุม BI tier, data products, governance, ความต่าง UAT/production และเกณฑ์รับมอบ
- [UAT Compose](../../compose/docker-compose.insight-uat.yml) แยก Superset, PostgreSQL metadata และ Redis cache; PostgreSQL มี named volume ใหม่ ส่วน Redis เป็น cache ชั่วคราว
- [Superset image/config](../../insight/Dockerfile), bootstrap admin ที่ไม่เปลี่ยน account เดิม และ [ตัวสร้าง demo bundle](../../insight/build_demo_bundle.py) สำหรับ dataset, 5 charts และ dashboard ตัวอย่างที่ยังไม่ publish
- [UAT runbook](../../runbooks/07_kingpac_insight_uat.md), การเชื่อม UAT image เข้ากับ workflow ที่มีอยู่ และการปรับ UAT/production architecture
- [ADR](../../adr/0006-kingpac-enterprise-insight-platform.md), [PoC plan](KINGPAC_INSIGHT_POC_PLAN.md) และ [deployment blueprint](../architecture/KINGPAC_INSIGHT_DEPLOYMENT_BLUEPRINT.md) ที่เทียบกับรายงานที่ผู้ใช้คัดลอกมา
- แก้ dbt AOV จากค่าเฉลี่ยต่อ line เป็นยอดรวมต่อ distinct order แบบ provisional พร้อม dbt unit-test fixture และ offline regression test
- API CORS default ปิด cross-origin พร้อม explicit allowlist; optional Grafana ClickHouse UAT image/override และ read-only branch-isolation audit tool

## หลักฐานที่รันในเครื่องพัฒนา

| การตรวจ | คำสั่ง/วิธีที่รัน | ผลจริงและขอบเขต |
|---|---|---|
| Compose syntax | `docker compose -f compose/docker-compose.insight-uat.yml config --quiet` โดยตั้ง test-only environment variables ใน process | Exit 0; ตรวจ interpolation/schema เท่านั้น ไม่ได้ติดต่อ Docker daemon |
| Compose: API/Grafana | `docker compose -f compose/docker-compose.dev.yml --profile api config --quiet` และ merge `docker-compose.observability.yml` กับ `docker-compose.insight-grafana-uat.yml` โดยใช้ test-only environment | ทั้งสอง exit 0; ไม่ได้ start containers |
| BI unit tests | `uv run --no-project --python 3.14 python -m unittest discover -s insight/tests -v` | 13 tests, `OK`; ทดสอบ config, bootstrap และ branch isolation แบบ mock รวมทั้งความสัมพันธ์ของ assets |
| API CORS | `uv run --no-project --python 3.14 --with fastapi --with httpx --with requests python -m unittest discover -s api/tests -v` | 4 tests, `OK`; ใช้ FastAPI TestClient ไม่ได้ทดสอบ reverse proxy หรือ authentication |
| AOV offline | `uv run --no-project --python 3.14 python -m unittest discover -s dbt/tests_offline -v` | 1 test, `OK`; ใช้ SQLite ในหน่วยความจำแทน ClickHouse เฉพาะตรวจผลรวม/กรอง/หลาย lines |
| dbt parse / registration | dbt-core 1.8.6 + dbt-clickhouse 1.8.4: `dbt parse --no-partial-parse` และ `dbt ls --select test_type:unit` ด้วย temporary profile | Exit 0; `Found ... 1 unit test`, ชื่อ `sales_aov_is_revenue_per_order_not_per_line`; ขั้นตอน parse/ls เองไม่ได้รัน test |
| Docker / Superset + ClickHouse | Build `insight/Dockerfile`; เริ่ม Compose ใน project/network แยก, import dashboard และเรียก chart-data API ด้วย synthetic ClickHouse 26.8.40.7 | Image build และ dependency check ผ่าน; Superset, PostgreSQL, Redis healthy; import ได้ 1 dashboard/5 charts; API คืนยอด 100, orders 2, customers 2, quantity 3 ตาม fixture |
| dbt unit test บน ClickHouse | Build `dbt/Dockerfile`; `dbt test --select test_type:unit` ผ่าน network/profile ของ sandbox | `PASS=1 WARN=0 ERROR=0 SKIP=0 TOTAL=1`; ทดสอบ fixture เท่านั้น ไม่ยืนยันข้อมูลธุรกิจจริง |
| Grafana / ClickHouse | Build UAT base และ optional Grafana image; เรียก Grafana datasource health API กับ synthetic ClickHouse | Plugin 4.14.1 build ไม่ผ่านเพราะไม่มีใน Grafana registry; เปลี่ยนเป็น 4.14.0 แล้ว build ผ่าน และ health API ตอบ `200 OK`, `Data source is working` |
| SQL / Grafana YAML | ลบ dbt Jinja config/ref แล้วตรวจ gold SQL ด้วย `sqlglot` ClickHouse dialect; parse optional Grafana datasource ด้วย PyYAML | Parser ผ่าน; ไม่ได้ยืนยัน ClickHouse execution หรือ Grafana plugin/runtime |
| Lint / Python 3.11 | `ruff check api/main.py api/tests insight dbt/tests_offline` และรันชุด tests ทั้งสามด้วย Python 3.11 | Ruff `All checks passed`; tests 13 + 4 + 1 ผ่าน; เป็น local checks ไม่ใช่ image build |
| Bundle | รัน `build_demo_bundle.py` ไปยัง temporary ZIP และ `python -m zipfile -t` | สร้าง ZIP และตรวจ integrity สำเร็จ; ไม่ใช่การ import เข้า Superset จริง |
| Import schema | โหลดคลาส schema dataset/chart/dashboard จาก source Superset tag `6.1.0` และตรวจ assets ด้วย Marshmallow 3.26.2 ใน harness ที่ใช้ stubs บางส่วน | 7 assets ผ่าน field schema; ไม่ได้ตรวจ database schema หรือ import/runtime จริง |
| Drivers | สร้าง SQLAlchemy engines โดยใช้ `sqlalchemy==1.4.54`, `clickhouse-connect==1.13.0` และ `psycopg2-binary==2.9.13` ใน Python 3.14 บน Windows | Dialect `clickhousedb` และ `postgresql` load ได้; ไม่ได้เปิด connection และไม่ใช่ environment ภายใน image |
| Python/shell | `python -m compileall -q insight` และ Git Bash `bash -n insight/init.sh` | Exit 0; ตรวจ syntax เท่านั้น |
| Git whitespace | `git diff --check` | Exit 0 สำหรับ tracked changes; มีคำเตือน Git เรื่อง line endings บน Windows |

ภายหลังผู้ใช้เปิด Docker Desktop แล้ว client/server เป็น `29.9.3` และรัน local sandbox ตามตาราง. ClickHouse account ใน sandbox เป็น account สำหรับทดสอบที่มีสิทธิ์สูง จึง **ไม่ใช่หลักฐาน least privilege หรือ RLS**. ยังไม่ได้ทดสอบ browser rendering, SSO, RLS, performance, backup/restore, image vulnerability scan หรือ deployment บน UAT ขององค์กร. Superset แจ้งเตือนว่า rate-limit storage เป็น in-memory; production multi-instance ต้องกำหนด shared backend และทดสอบ

หลังทดสอบได้ลบเฉพาะ project `kpinsightverify20261119`, test containers/network/volume ที่สร้างในงานนี้ และ temporary credentials. ตรวจหลัง cleanup พบว่า containers `docker-api-1`, `docker-web-1`, `docker-mssql-1`, `docker-minio-1` ซึ่งเห็นขณะเริ่มงานไม่ปรากฏแล้ว; ยังไม่ทราบสาเหตุ. คำสั่ง cleanup ที่รันระบุเฉพาะชื่อ test resources ข้างต้น และไม่ได้สั่งลบ containers เหล่านั้น

## งานก่อนใช้งานจริง

1. รายงานที่ผู้ใช้คัดลอกมาได้รับแล้ว; ทำ traceability ใน PoC plan และให้เจ้าของผลิตภัณฑ์ตรวจความครบถ้วน
2. ทำ UAT integration บน infrastructure ขององค์กรตาม runbook; ตรวจ browser render, filter, role/permissions, TLS proxy และคุณภาพข้อมูลกับ Power BI
3. ให้ Data Owner/Finance อนุมัติ KPI และ reconciliation; sample fact อาจซ้ำและไม่มี status, silver sorting key ไม่มี line identifier จึงยังยืนยัน net revenue หรือ completed orders ไม่ได้. รัน dbt unit test บน ClickHouse sandbox
4. ออกแบบ/สร้างและทดสอบ production SSO/MFA, per-user data isolation, Celery scheduling, HA ของ Superset/PostgreSQL/Redis, monitoring/audit, backup/restore และ CI scan; ระบุ sizing, DNS, TLS, retention และ approved RPO/RTO
5. แนบหลักฐาน security, load, failover และ restore รวมทั้ง human sign-off ก่อน production promotion

## ผลกระทบและ rollback

ไม่ได้แก้ `sql/init` หรือ ClickHouse users/volumes เดิม แต่แก้ dbt gold model: การรัน dbt จะเปลี่ยนผล AOV และอาจ rebuild table จึงต้องตรวจ downstream, backfill และ rollback ก่อนรัน. มี PostgreSQL metadata volume เพิ่มเมื่อ deploy; `superset db upgrade` เปลี่ยน metadata schema และ rollback image อย่างเดียวอาจไม่พอ ต้องมี backup และ key ที่ตรงกัน

API browser clients ข้าม origin ที่เคยใช้ wildcard ต้องตั้ง allowlist; CORS ไม่ใช่ authentication. Optional Grafana image เปลี่ยน plugin path จนอาจไม่โหลด plugins เดิม; inventory และ rollback ตาม blueprint. `scripts/validate_stack.sh` วนตรวจทุก Compose จึงต้องมี test-only values สำหรับ `INSIGHT_SUPERSET_IMAGE`, `SUPERSET_SECRET_KEY`, `INSIGHT_POSTGRES_PASSWORD`, `INSIGHT_ADMIN_USERNAME`, `INSIGHT_ADMIN_EMAIL`, `GRAFANA_INSIGHT_UAT_IMAGE`, `INSIGHT_GRAFANA_CH_HOST`, `INSIGHT_GRAFANA_CH_USER` และ `INSIGHT_GRAFANA_CH_PASSWORD` เพิ่มจาก variables เดิม; ห้าม log secrets

## Handoff Contract

- **Scope & Sources Inspected:** รายงานที่ผู้ใช้คัดลอก, AGENTS.md, existing UAT/production architecture, ClickHouse SQL/RBAC, dbt, API, Grafana, semantic catalog และ vendor docs
- **Assumptions & Decisions:** Sales pilot สำหรับ UAT ใช้ข้อมูลที่มีอยู่; AOV เปลี่ยนตาม catalog แบบ provisional; ออกแบบ production เป็น multi-host target
- **Security & Operational Impact:** เพิ่ม metadata/cache และ PostgreSQL volume; shared BI credential ไม่ให้ per-user database isolation; CORS default เปลี่ยน; secret key ต้องเก็บคู่กับ metadata backup
- **Validation Commands & Results:** ตามตารางผลจริงข้างต้น; มี local synthetic runtime evidence แต่ไม่มี security scan หรือ recovery evidence
- **Remaining TBDs & Residual Risks:** Infrastructure/secrets, line identity/CDC, BI KPI/RLS, image build/integration, scheduling, HA, SSO, backup และ RPO/RTO
- **Human Approval Required:** Independent reviewer หรือ human domain owner ต้องตรวจงาน; Data Owner/Finance, Security, Platform/SRE, DBA, Network และ CAB อนุมัติตามขอบเขต UAT/production
# Production candidate update — 2026-11-19

ผู้ใช้ยืนยันว่าใช้ Keycloak/OIDC ภายใน และมี PostgreSQL HA กับ Redis TLS แล้ว แต่ endpoint, certificates, group mapping และการทดสอบจริงยังเป็น TBD. เพิ่ม `compose/docker-compose.insight-prod.yml`, `insight/Dockerfile.prod`, production configuration, OIDC group checks, basic preflight และ [production runbook](../../runbooks/08_kingpac_insight_production.md). เป็น candidate สำหรับ review และ UAT เท่านั้น; ยังไม่ได้ deploy production หรือพิสูจน์ HA, MFA, RLS, TLS integration, backup/restore, performance และ vulnerability scan. Scheduled reporting ยังไม่ได้ implement ใน production candidate.

Local validation: production candidate image build สำเร็จจาก local UAT base; test 6 กรณีบน image ผ่าน (synthetic claims/config); `docker compose ... config --quiet` ผ่านด้วย dummy values; preflight เมื่อไม่มี inputs ปฏิเสธตามที่ออกแบบ. ผลเหล่านี้ไม่ใช่ production integration test หรือ security approval. Image build แจ้งเตือน `InvalidDefaultArgInFrom` เพราะต้องส่ง base image ผ่าน build argument; production ต้อง pin reviewed base และ image digest. ดูวิธีนำขึ้นระบบ ผลกระทบ volume/rollback และรายการ approval ใน runbook.

