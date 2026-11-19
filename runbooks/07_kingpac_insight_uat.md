# Runbook 07: KingPac Enterprise Insight Platform — UAT

สำหรับผู้ดูแล UAT บน Ubuntu 24 LTS และ Docker Compose V2/Portainer Git-backed Stack. อ่าน [Solution Architecture](../docs/architecture/KINGPAC_ENTERPRISE_INSIGHT_PLATFORM.md) ก่อนใช้งาน. Stack นี้เป็น single-host และไม่ใช่ HA; ห้ามใช้ข้อมูล production ที่ไม่ได้รับอนุญาตหรือไม่ได้ mask

สำหรับ optional Grafana–ClickHouse provisioning และ API CORS compatibility ดู [Deployment Blueprint](../docs/architecture/KINGPAC_INSIGHT_DEPLOYMENT_BLUEPRINT.md); สำหรับ branch-isolation audit, KPI contracts และเกณฑ์ benchmark ดู [PoC Plan](../docs/implementation/KINGPAC_INSIGHT_POC_PLAN.md)

## 1. สิ่งที่ต้องเตรียม

1. UAT Lakehouse Core ทำงานแล้ว และ `lakehouse-uat-integration` เป็น Docker network เดียวกับ ClickHouse; ยืนยันชื่อ container/DNS และว่า `mart.fact_sales` มี synthetic/masked data
2. จัดเตรียม image registry ที่ UAT host/Portainer ดึงได้, outbound access สำหรับ build ที่ได้รับอนุมัติ และ disk สำหรับ image กับ PostgreSQL metadata volume. ภาพขนาด/sizing ยังต้องวัดจริง
3. จัดเตรียม secret manager หรือ Portainer environment ที่จำกัดสิทธิ์: Superset secret key แบบสุ่มอย่างน้อย 32 ตัวอักษรและไม่ซ้ำ environment, PostgreSQL password และ initial admin password อย่างน้อย 16 ตัวอักษร. เก็บ admin credential อย่างปลอดภัย ห้ามส่งลง Git, chat หรือ logs
4. หากผู้ใช้อื่นต้องเข้าเว็บ ให้ Network/Security ตั้ง trusted reverse proxy บน host ที่เข้าถึง `127.0.0.1:18088` พร้อม TLS, authentication policy และ approved CIDR/VPN. Proxy ต้องลบ/เขียนทับ `X-Forwarded-*` จาก client; ตั้ง `INSIGHT_HTTPS_ENABLED=true` เฉพาะเมื่อ proxy ที่เชื่อถือได้ทำงานจริง
   Docker integration network ที่ใช้ร่วมกับ ClickHouse อาจเข้าถึง listener `8088` ภายใน container โดยไม่ผ่าน proxy ได้ จึงต้องจำกัดสมาชิก network และกำหนด network controls เพื่อให้การเชื่อถือ forwarded headers มีผลจริง; อย่าเพิ่ม workload ที่ไม่เชื่อถือใน network นี้
5. ตรวจ availability และ vulnerability policy ของ images และ dependencies. ตัวอย่าง pin PostgreSQL 16.16, Redis 7.4.12 และ Superset 6.1.0 ตาม digest ที่ระบุใน files; การ pin ไม่ใช่หลักฐานว่า scan ผ่าน
   Driver versions ถูก pin เฉพาะ dependencies โดยตรง; transitive dependencies ยังไม่ได้ lock/hash. จัดทำ SBOM, dependency locking และ scan ตาม policy ก่อน production

## 2. Build และ publish image

จาก repository root บน build host หรือ CI:

```bash
docker build -f insight/Dockerfile -t kingpac-insight-superset:uat-6.1.0 .
```

สำหรับ Portainer Git Stack ให้ส่ง image ผ่าน CI ไป UAT registry ที่อนุมัติ แล้วตั้ง `INSIGHT_SUPERSET_IMAGE` เป็น reference ที่ host ดึงได้ โดยควรระบุ digest. [UAT publishing workflow](../.github/workflows/publish-uat-images.yml) มี `kingpac-insight-uat` ใน matrix และตรวจ import dependencies/unit tests ก่อน push; workflow นั้นยังต้องรันจริงและบันทึกผล. Production ต้องผ่าน Jenkins → Harbor → Trivy ตามนโยบาย ไม่ใช่นำ UAT image ขึ้น production โดยตรง

## 3. Environment และ Portainer

กำหนดค่าผ่าน Portainer/secret manager หรือไฟล์นอก Git ที่จำกัดสิทธิ์ผู้ดูแล (`chmod 600`). ตัวอย่างชื่อคีย์ด้านล่างเป็นชื่อ configuration เท่านั้น ไม่ใช่ secret values:

| Key | ค่า/การตัดสินใจ |
|---|---|
| `INSIGHT_SUPERSET_IMAGE` | image ที่ build แล้วและ UAT endpoint ดึงได้; registry/digest `TBD` |
| `SUPERSET_SECRET_KEY` | ค่าสุ่มยาวจาก secret manager; สำรองแยกอย่างปลอดภัยและคงค่าเดิมเมื่อ restart |
| `INSIGHT_POSTGRES_PASSWORD` | รหัสผ่าน PostgreSQL metadata; ห้ามเปลี่ยนค่า env แล้วคาดหวังว่า PostgreSQL volume เดิมเปลี่ยนรหัสผ่านเอง |
| `INSIGHT_POSTGRES_USER`, `INSIGHT_POSTGRES_DB` | ค่าเริ่มต้น `insight`; ตั้งก่อนสร้าง volume และอย่าเปลี่ยนโดยไม่มีแผน migration |
| `INSIGHT_ADMIN_USERNAME`, `INSIGHT_ADMIN_EMAIL` | UAT bootstrap admin ที่กำหนดโดยผู้ดูแล |
| `INSIGHT_ADMIN_PASSWORD` | รหัสผ่านเริ่มต้น อย่างน้อย 16 ตัว; เมื่อ account มีอยู่แล้ว init จะไม่แก้/หมุนรหัสผ่าน สามารถนำตัวแปรนี้ออกหลัง bootstrap |
| `INSIGHT_PORT` | host loopback port; default `18088` |
| `INSIGHT_HTTPS_ENABLED` | `false` สำหรับการทดสอบผ่าน localhost; `true` หลัง trusted TLS proxy พร้อมและทดสอบแล้ว |
| `INTEGRATION_NETWORK` | ค่า default `lakehouse-uat-integration`; เปลี่ยนเฉพาะกรณี UAT network ชื่ออื่น |
| `INSIGHT_POSTGRES_IMAGE`, `INSIGHT_REDIS_IMAGE` | optional override เป็น approved pinned image/digest |

ใน Portainer สร้าง stack ใหม่จาก Git repository/ref ที่ผ่าน review โดยใช้ Compose path `compose/docker-compose.insight-uat.yml`. ใส่ environment ผ่านช่องที่เข้าถึงได้เฉพาะผู้ดูแล; อย่าใส่ secret ใน URL หรือ commit. ก่อน deploy ตรวจว่า external integration network มีอยู่แล้วบน Docker endpoint เดียวกัน และ image ใน registry มีสิทธิ์ pull. การ deploy stack นี้ไม่ควรสร้างหรือเปลี่ยน ClickHouse volume

บน shell ผู้ดูแลสามารถตรวจ config โดยใช้ private env file และไม่แสดงค่าลงหน้าจอ:

```bash
docker compose --env-file /secure/path/kingpac-insight.env -f compose/docker-compose.insight-uat.yml config --quiet
docker compose --env-file /secure/path/kingpac-insight.env -f compose/docker-compose.insight-uat.yml up -d
docker compose --env-file /secure/path/kingpac-insight.env -f compose/docker-compose.insight-uat.yml ps
```

`/secure/path/kingpac-insight.env` เป็นตัวอย่าง path; ผู้ดูแลจัดการไฟล์และ secret เอง. `init` รัน metadata migrations แล้วสร้าง local admin หากยังไม่มี. Container init ที่ exit code 0 เป็นผลลัพธ์ปกติ; หากไม่ผ่านให้ดู logs โดยปกปิด secrets และแก้สาเหตุก่อน restart. ห้ามลบ metadata volume

## 4. ติดตั้ง dashboard ตัวอย่าง

เมื่อ Superset healthy และ login ด้วย UAT admin ได้แล้ว ให้สร้าง bundle และ import **ครั้งแรกเท่านั้น**:

```bash
docker compose --env-file /secure/path/kingpac-insight.env -f compose/docker-compose.insight-uat.yml exec superset python /app/kingpac/build_demo_bundle.py /tmp/kingpac-demo.zip
docker compose --env-file /secure/path/kingpac-insight.env -f compose/docker-compose.insight-uat.yml exec superset superset import-dashboards -p /tmp/kingpac-demo.zip -u UAT_ADMIN_USERNAME
```

แทน `UAT_ADMIN_USERNAME` ด้วย username ที่สร้างจริง ซึ่งไม่ใช่ password. การ import ซ้ำอาจ replace layout/relationships ของ dashboard ที่ UUID เดิมและไม่ใช่วิธีอัปเดต definition ของ assets ทั้งหมด; export/backup และ review ผลกระทบก่อน import ซ้ำ

ใน Superset administrator UI เปิด connection **KingPac ClickHouse UAT**, ระบุ credentials `bi_user` จาก secret manager, ทดสอบ connection แล้วบันทึก. ตัว bundle ไม่มี password; hostname เริ่มต้น `lakehouse-clickhouse-dev`, HTTP port `8123`, database `mart` ใช้ได้เฉพาะเมื่อ stack อยู่บน network เดียวกันและชื่อ DNS นี้ตรงกับ UAT จริง. หากใส่ SQLAlchemy URI ใน UI ให้ URL-encode อักขระพิเศษใน username/password; อย่าส่ง URI ที่มี credentials ลง chat, Git หรือ command history. การเชื่อมต่อ UAT นี้เป็น HTTP ภายใน Docker network; production ต้องใช้ TLS ตาม topology ที่อนุมัติ

เปิด dashboard **KingPac Sales Overview — UAT** และตรวจ time/branch filters กับข้อมูลสังเคราะห์. Dashboard สร้างในสถานะ unpublished: owner ต้อง review ก่อน publish ให้กลุ่ม UAT ที่อนุมัติ. ไม่มีสิทธิ์ผู้ใช้หรือ RLS ที่สร้างให้โดยอัตโนมัติ; ห้ามเปิดข้อมูลหลายสาขาที่มีข้อจำกัดโดยยังไม่ทดสอบ data isolation

## 5. การตรวจรับ UAT

บันทึกวันที่, Git SHA, image digest, ผู้ทดสอบ และ output ที่ไม่เปิดเผย secret:

1. `docker compose ... config --quiet` ผ่าน; `ps` แสดง `metadata`, `cache`, `superset` healthy และ `init` exit 0
2. จาก host `curl -fsS http://127.0.0.1:18088/health` ตอบสำเร็จ; ทดสอบ URL ผ่าน TLS proxy และ secure cookie เมื่อเปิด HTTPS
3. ผ่าน Superset UI: database test สำเร็จ, dataset `mart.fact_sales` อ่านได้, ทั้งห้า charts render, ช่วงเวลาและ branch filters เปลี่ยนผลถูกต้อง; ทดสอบ range ว่าง, ไม่มีข้อมูล, และ query ล้มเหลว
4. เทียบยอดจาก fact กับ dashboard ในช่วง/branch เดียวกัน: `sum(amount)`, `uniqExact(_source_system, order_id)`, `uniqExact(customer_id)`, `sum(quantity)`. ทดสอบกรณี order หลายบรรทัดและลูกค้าคนเดิมหลายวัน; ตรวจ sample load ซ้ำและให้ owner ตัดสิน duplicate/cancellation rule
5. ทดสอบ negative access ของบัญชี BI ต่อ `raw`, `core`, INSERT/DDL และการเข้าถึงข้าม branch ผ่าน chart/export/API/SQL Lab ตามนโยบายที่ออกแบบจริง; shared service account และการมี filter เพียงอย่างเดียวไม่ใช่ RLS
6. ทดสอบ metadata backup/restore ใน environment แยก โดยใช้ key ที่ตรงกัน และยืนยัน dashboard, users/roles และการถอดรหัส connection. แยก ClickHouse backup/restore drill ตาม [Runbook 02](02_backup_and_restore_operations.md). จนกว่าผลเหล่านี้ผ่านจริงให้ถือเป็น `TBD`

สำหรับ dbt AOV ให้รัน unit test `sales_aov_is_revenue_per_order_not_per_line` ใน sandbox ที่มี dbt profile/fixture พร้อม แล้วแนบ output. สูตรเป็น provisional และยังต้องตรวจ source line identity, CDC/tombstone, cancelled/completed status และการรับรองจาก Finance; การ parse model ไม่ใช่การรัน test

ตัวอย่าง `curl` ข้างต้นต้องใช้ port ที่ตั้งจริง. ไม่ใช้คำสั่งแสดง environment หรือ `docker compose config` แบบเต็มในหลักฐาน เพราะอาจแสดง secrets

## 6. การปรับรุ่นและกู้คืน

ก่อนเปลี่ยน Superset image/config ให้ snapshot/backup PostgreSQL metadata และเก็บ secret key คู่กันในระบบสำรองที่ได้รับอนุมัติ จากนั้นทดสอบ migration และ restore ใน environment แยก. `init` อาจรัน `superset db upgrade` อีกเมื่อ redeploy; metadata schema ที่อัปเกรดแล้วอาจใช้กับ image เก่าไม่ได้. Rollback ต้องอาศัย backup ที่ผ่าน restore drill และ image/key ที่ตรงกัน; การย้อน Git ref อย่างเดียวไม่ย้อน schema หรือข้อมูล. อย่าใช้ `docker compose down -v` และอย่าลบ volumes โดยไม่มี written approval และ verified backup

ถ้า cache ล่ม dashboard/filter operations อาจผิดพลาดได้; แก้ Redis แล้วตรวจ health และรีเฟรช dashboard. หาก login ไม่ได้ ตรวจ proxy/TLS, secure cookie, admin/IdP และ logs ที่ปกปิดข้อมูล. หาก chart ผิด ให้ตรวจ database connection, permissions, `mart.fact_sales`, ช่วงวันที่และผล reconciliation ก่อนแก้ chart

## Handoff Contract

- **Scope & Sources Inspected:** UAT Compose, Superset image/config, demo bundle, ClickHouse fact/RBAC และ UAT Git Stack runbook
- **Assumptions & Decisions:** ใช้ synthetic/masked UAT; internal ClickHouse HTTP; trusted TLS proxy แยก; ไม่มี HA, worker หรือ scheduled reports
- **Security & Operational Impact:** เพิ่ม metadata volume; local bootstrap admin, private unauthenticated UAT Redis และ read-only BI service account ต้องควบคุมตามที่ระบุ
- **Validation Commands & Results:** คำสั่งใน runbook เป็นขั้นตอนให้ผู้ดูแลรัน ไม่ใช่การอ้างว่ารันผ่านแล้ว
- **Remaining TBDs & Residual Risks:** Registry/DNS, secrets, HTTPS proxy, dataset quality, BI role/RLS, image scan, runtime integration และ restore evidence
- **Human Approval Required:** Platform, Security, DBA และ Data Owner สำหรับ UAT sign-off; production promotion ต้องผ่านผู้อนุมัติตาม architecture
