# แผนงานผู้เชี่ยวชาญเฉพาะด้านเพื่อยกระดับ UAT สู่ระบบใช้งานจริง

**สถานะ:** รายการวิเคราะห์จาก repository ณ 2026-11-02; **ยังไม่ผ่าน Production Readiness Gate** และไม่มีการ deploy หรือทดสอบ live environment ในงานรอบนี้  
**นโยบายหลัก:** [AGENTS.md](../AGENTS.md) · **ทีมที่เรียกใช้งานได้:** [agents/README.md](../agents/README.md) · **เกณฑ์ปล่อยระบบ:** [Production runbook](../runbooks/04_portainer_prod_deployment.md)

## วิธีใช้แผนนี้

ผู้ประสาน A00 เปิดงานหนึ่งรายการต่อหนึ่งการเปลี่ยนแปลง โดยบันทึกเจ้าของ ผู้ตรวจทานอิสระ หลักฐานก่อน/หลัง ผลกระทบและ rollback. P0 คือเงื่อนไขที่ต้องปิดก่อนเสนอ production; P1 คือความสามารถและความทนทานที่ต้องจัดลำดับตาม workload จริง. คำว่า “ผ่าน” หมายถึงมีผลคำสั่งและรายงานจากสภาพแวดล้อมที่ระบุ ไม่ใช่การมีไฟล์หรือ container/stack ปรากฏใน Portainer. ผล UAT แบบ host เดียวไม่รับรอง HA.

## P0: ข้อกีดขวางการใช้งานจริง

| ID / เจ้าของ → ผู้ตรวจทาน | หลักฐานปัจจุบัน | งานออกแบบ/ปรับปรุง และเกณฑ์ตรวจรับ |
| --- | --- | --- |
| P0-01 A01+A03+A05 → A02+A07+A08 | [medallion DDL](../sql/init/02_medallion_tables.sql) ใช้ `MergeTree`/`ReplacingMergeTree`; [serving MV](../sql/init/03_materialized_views.sql) ใช้ `AggregatingMergeTree`; ไม่มี `Replicated*`/`ON CLUSTER` ใน SQL init. Compose production สอง node จึงยังไม่พิสูจน์ data replication | ออกแบบ replicated tables, Keeper paths, distributed DDL, migration/backfill และ rollback; ตรวจ syntax บน ClickHouse เวอร์ชันเป้าหมาย, ยืนยัน counts/checksums และ replication queues ทั้งสอง replica, แล้วทำ host-loss/rejoin drill ใน isolated environment. ห้ามกล่าวอ้าง HA จนมีผลทดสอบข้าม failure domains |
| P0-02 A04+A02 → A08+A10 | [orchestrator](../orchestration/pipeline_orchestrator.py) เรียก [sample ingestion](../ingestion/sample_ingestion.py) ซึ่งสร้างข้อมูลสังเคราะห์และเติม `mart.fact_sales` โดยตรง; ยังไม่ใช่ source → S3/Parquet → raw → core → mart ที่ครบ | แยก demo generator จาก production pipeline; ออกแบบ landing object, lineage/metadata, idempotent load, replay และ mart publishing path เดียว; ทดสอบด้วย source fixture และ object/row/hash reconciliation บน UAT |
| P0-03 A04+A05 → A08 | [dbt Dockerfile](../dbt/Dockerfile) นำเข้า project ที่มีเพียง `profiles.yml.example` ขณะที่ orchestration เรียก `--profiles-dir .` | จัดหา runtime profile แบบไม่ใส่ secret ลง Git และผูก environment ที่ถูกต้อง; เก็บผล `dbt debug`, `compile`, `run`, `test` จาก UAT และยืนยันว่าตารางเป้าหมายตรงกับ serving |
| P0-04 A04+A06 → A02+A08 | [reconciliation](../data_quality/reconciliation.py) แปลง query error เป็น 0 และใช้ API account ที่อ่าน raw/mart ไม่ได้ตาม [RBAC](../sql/init/04_rbac_and_row_policies.sql) | แยก quality service role แบบ least privilege; query failure ต้อง exit nonzero และห้ามได้คะแนนผ่าน; ทดสอบ positive, SQL error, สิทธิ์ไม่พอ, count/amount/hash mismatch ด้วย fixture |
| P0-05 A10+A02+A04 → A08+Data Owner | [generator](../ingestion/sample_ingestion.py) ใช้ `PROCESSING`/`SHIPPED` แต่ [orders contract](../contracts/orders_contract.yml) ไม่อนุญาต; contract validator ยังแยกจาก ingest | Data Owner อนุมัติค่าธุรกิจและเวอร์ชัน contract; ตรวจ contract ก่อน write, quarantine/error path และทดสอบ valid/invalid/replay batch |
| P0-06 A12+A06 → A08 | [API `/top-products`](../api/routers/sales.py) อ่าน `mart`/`core` แต่ [API role](../sql/init/04_rbac_and_row_policies.sql) ได้สิทธิ์ `serving.*`; [API main](../api/main.py) ใช้ wildcard CORS และ health แบบ process | ย้าย query ไป serving view ที่อนุมัติหรือแก้ contract/สิทธิ์ตาม review; กำหนด auth, trusted proxy/TLS, origin allowlist, limits และ dependency readiness; ทดสอบทุก route ด้วย `api_user` พร้อมกรณี unauthorized/forbidden |
| P0-07 A07+A06 → A08+Operations Owner | [backup](../scripts/backup_clickhouse.sh) ครอบคลุมเพียง `mart`, `curl -sS` อาจไม่ fail เมื่อ HTTP/SQL error; [restore drill](../scripts/restore_test.sh) ใช้ชื่อ database คงที่และตรวจเพียง row count | กำหนด recovery scope ทุกฐาน/metadata ที่ต้องใช้, secret injection และ independent S3; error ต้อง exit nonzero; restore ไป namespace แยกที่ตรวจว่าปลอดภัย, ตรวจ inventory/count/aggregate/hash, วัด RPO/RTO ที่ business อนุมัติ; cleanup เฉพาะเป้าหมาย drill พร้อม human gate |
| P0-08 A05+A06+A07 → A08+Platform/Security Owners | [production runbook](../runbooks/04_portainer_prod_deployment.md) ระบุ unpinned image, relative bind mounts, S3/KMS, TLS, LB, Keeper config, service-account env, prod observability และ ingestion topology ที่ยังไม่ปิด | ปิด checklist ทีละข้อด้วย config review, `docker compose config`, XML/SQL parser, image digest/scan, network/TLS and cross-host tests, failover/rollback evidence; ค่าองค์กรที่ยังไม่กำหนดเป็น `TBD` |

## P1: ประสิทธิภาพ ความน่าเชื่อถือ และการดูแลระยะยาว

| ID / เจ้าของ → ผู้ตรวจทาน | งานและเกณฑ์ตรวจรับ |
| --- | --- |
| P1-01 A04 → A02+A08 | เปลี่ยน local watermark และ error-to-empty/partial ใน [connectors](../ingestion/connectors/) เป็น durable checkpoint, explicit failure และ idempotent batch; file archive หลัง commit เท่านั้น; ทดสอบ crash/replay/duplicate |
| P1-02 A02+A03+A04 → A08+A10 | กำหนด CDC tombstone/version semantics ใน [silver model](../dbt/models/silver/silver_orders_cleaned.sql) และเชื่อม dbt gold กับ serving ตาม source of truth เดียว; ทดสอบ update/delete/replay และ query ที่ใช้ `FINAL`/argMax ตามแบบที่อนุมัติ |
| P1-03 A04+A10 → A08 | เพิ่ม freshness, uniqueness, accepted values, relationships และ threshold ใน [dbt source tests](../dbt/models/bronze/sources.yml); รายงานผลบน dataset ที่ระบุ |
| P1-04 A07+A05 → A08 | ทำ observability topology สำหรับ management zone; ตรวจ scrape target, alert firing/delivery และ log collection จริง. [Loki config](../monitoring/loki/loki-config.yml) อย่างเดียวไม่แสดงว่ามี shipper |
| P1-05 A11+A03+A07 → A08 | ทำ benchmark ที่ระบุ workload, concurrency, dataset, host, ClickHouse version และ date; วัด p50/p95/p99, throughput, CPU/RAM/disk, parts/merges, S3 traffic และ cost/headroom; เทียบ failure-domain scenario |
| P1-06 A12+A06 → A08 | ประเมิน [AI helpers](../ai_assistant/) ด้วยชุดคำถาม/ข้อมูลที่อนุมัติ, negative tests, prompt injection และ audit; demo vector/text-to-SQL/anomaly ไม่ถือเป็น production AI จนผ่านเกณฑ์ |
| P1-07 A05+A06 → A08 | ตรวจ least privilege ของ `etl_service` และ `monitoring_service` ใน [RBAC](../sql/init/04_rbac_and_row_policies.sql), ใช้ secret scanner และ image scan ที่มีผลบันทึก; pattern grep ใน CI ไม่ใช่หลักฐานว่าไม่มี secret |

## ลำดับการทำงานและหลักฐานส่งมอบ

1. **ขอบเขตข้อมูลและ NFR:** A10/Data Owner ระบุ source, KPI, latency, quality, retention, classification; A11 เก็บ workload, A07 รับ RPO/RTO ที่ business ลงนาม. ที่ยังไม่ทราบให้เป็น `TBD`.
2. **สถาปัตยกรรมและความปลอดภัย:** A01/A03/A05/A06 ปิด P0-01, P0-06, P0-08 ด้วย ADR, topology และ migration/rollback design ที่ตรวจทานแล้ว.
3. **เส้นทางข้อมูลและกู้คืน:** A02/A04/A07 ปิด P0-02 ถึง P0-05 และ P0-07 ใน UAT แยกจาก production. เก็บคำสั่ง ผลลัพธ์ และ artifact ที่ไม่เผย secret.
4. **การท้าทายอิสระ:** A08 ทวน code/config, รัน validation ที่เหมาะสม, บันทึกผลที่ล้มเหลว, ยืนยัน coverage ของ static เทียบกับ live test. A09 ปรับคู่มือ/ADR ตามพฤติกรรมจริง.
5. **Human gate:** Architecture, Data, Security, Platform/Operations, Business และ Release owners ลงนามตาม [production runbook](../runbooks/04_portainer_prod_deployment.md). การ deploy production, credential rotation หรือ destructive migration ไม่อยู่ในอำนาจ agent.

## ตัวแปรที่ยังเป็น TBD

แหล่งข้อมูลและเจ้าของจริง, source schema และปริมาณข้อมูล, KPI/quality thresholds, retention, availability target, production DNS/IP, TLS/secret manager, S3/KMS/bucket, image patch/digest ที่อนุมัติ, load balancer, capacity/budget, RPO/RTO ที่ business ลงนาม และตารางปฏิบัติการ incident/on-call. ห้ามเติมค่าเหล่านี้จากตัวอย่าง UAT.

## ขอบเขตหลักฐานในงานรอบนี้

รายการข้างต้นมาจากการตรวจไฟล์แบบ read-only ของผู้เชี่ยวชาญ platform/data/security และการเปรียบเทียบกับนโยบาย. **ยังไม่ได้รัน** ClickHouse, dbt, backup/restore, failover, network/TLS, vulnerability scan หรือ performance benchmark เพื่อยืนยันระบบที่กำลังทำงาน. การเปลี่ยนแปลงในเอกสารนี้เป็นแผนและไฟล์บทบาท ไม่เปลี่ยน Compose, SQL DDL หรือ runtime configuration.
