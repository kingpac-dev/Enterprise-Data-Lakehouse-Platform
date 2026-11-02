# คู่มือใช้งาน Enterprise Data Lakehouse Platform — UAT

> ขอบเขต: UAT แบบ single host บน Docker Engine/Compose V2 และ Portainer Git-backed Stacks ตาม [AGENTS.md](../AGENTS.md). ใช้ข้อมูล synthetic หรือ masked เท่านั้น. คู่มือนี้อธิบายการใช้งานระบบที่มีใน repository และวิธีเก็บหลักฐานจาก environment จริง โดยไม่ถือว่า UAT เป็น High Availability หรือการรับรอง Production.

## 1. สถานะที่ยืนยันได้และวิธีใช้คู่มือ

ผู้ดูแลแจ้งว่าติดตั้ง UAT แล้ว และภาพหน้า **Portainer > Environment > Stacks** ที่ให้มาแสดง stack entries สี่รายการ: `lakehouse-uat-core`, `lakehouse-uat-datasources`, `lakehouse-uat-streaming`, `lakehouse-uat-observability`. ภาพดังกล่าวยืนยัน **การมีรายการ Stacks ใน UI ณ เวลาที่ถ่าย**; ไม่แสดงสุขภาพ container, Git reference/image digest, การเชื่อมต่อ network, SQL data, alerting หรือผล restore. ให้ผู้ดูแลตรวจรายการเหล่านี้ตามขั้นตอนด้านล่าง และบันทึกผลจริงก่อนระบุว่า “ผ่าน”.

| ผู้ใช้ | เริ่มที่หัวข้อ | สิทธิ์ที่ควรใช้ |
| --- | --- | --- |
| Platform/Portainer operator | [ตรวจ 4 stacks](#2-ตรวจสถานะและเข้าใช้งาน-4-portainer-stacks), [งานประจำ](#15-รอบการปฏิบัติงานและหลักฐาน) | Portainer operator/approved role; admin เฉพาะงานจำเป็น |
| Data engineer | [Sources](#3-data-sources-uat), [ClickHouse](#6-clickhouse-medallion), [dbt](#7-dbt-transformation) | source read account, ETL/data engineer role |
| BI/API consumer | [Serving API](#8-serving-rest-api), [SQL/BI](#9-bi-dbeaver-power-bi-และ-sql) | `bi_user` หรือ service role ที่ได้รับอนุมัติ |
| SRE/Security | [Observability](#10-observability-prometheus-grafana-loki), [Backup/DR](#13-backup-restore-และ-dr) | monitoring/backup role, management VPN |
| Developer/QA | [Data quality](#11-data-quality-contract-catalog-และ-orchestration), [Validation](#14-การตรวจรับ-uat-และขอบเขตของผลทดสอบ) | sandbox/test credentials |

ใช้ `<UAT_HOST_OR_DNS>`, `<APPROVED_PORTAINER_URL>` และ `<APPROVED_SECRET_SOURCE>` เป็นค่าที่องค์กรกำหนดจริง (**TBD** ในเอกสาร). ห้ามบันทึก URL ภายในที่แท้จริง, token, password หรือ output ที่มี customer data ลง Git/รายงานสาธารณะ.

## 2. ตรวจสถานะและเข้าใช้งาน 4 Portainer Stacks

1. เข้า `<APPROVED_PORTAINER_URL>` ผ่าน management VPN ด้วย account ของตนเอง เลือก environment UAT แล้วเปิด **Stacks**.
2. ตรวจชื่อ stack ทั้งสี่ในตาราง จากนั้นเปิดทีละ stack เพื่อดู **Git repository/reference**, **Compose path**, image tags/digests, environment variables ที่ไม่ใช่ secret และ container list. ห้ามคัดลอกค่า secret ออกจาก Portainer ไปใส่เอกสาร.
3. ในหน้า **Containers** ตรวจ `running/healthy` และดู logs ของ container ที่ผิดปกติ. การเห็น “Control: Total” หรือ stack อยู่ในตาราง **ไม่ใช่ health check**.
4. ในหน้า **Networks** ตรวจ external networks `lakehouse-uat-integration` และ `lakehouse-uat-observability`. ในหน้า **Volumes** ตรวจว่ามี persistent volumes ที่คาดไว้; อย่าลบ volumes เพื่อแก้อาการเริ่มต้นไม่ผ่าน.
5. บันทึกเวลา, environment, Git SHA/tag, image digest, status, health endpoint และผู้ตรวจใน UAT change/evidence record. ขั้นตอน redeploy/rollback ใช้ [runbook 01](../runbooks/01_portainer_git_stack_deployment.md) และ [runbook 06](../runbooks/06_github_ghcr_uat.md).

| Stack ใน Portainer | Compose file | Services ตามไฟล์ | สิ่งที่ตรวจหลังเปิด |
| --- | --- | --- | --- |
| `lakehouse-uat-core` | [dev.yml](../compose/docker-compose.dev.yml) | MinIO, init job, ClickHouse; dbt runner (`tools`) และ FastAPI (`api`) เป็น profiles; RustFS (`rustfs`) เป็น optional | MinIO/ClickHouse healthy, bucket, 4 databases, profile ที่เปิดจริง |
| `lakehouse-uat-datasources` | [datasources.yml](../compose/docker-compose.datasources.yml) | PostgreSQL, MySQL, SQL Server + init, MongoDB | container health, masked/synthetic dataset, application account |
| `lakehouse-uat-streaming` | [streaming.yml](../compose/docker-compose.streaming.yml) | Redpanda, Console | broker healthy, topic, producer/consumer connectivity |
| `lakehouse-uat-observability` | [observability.yml](../compose/docker-compose.observability.yml) | Prometheus, Grafana, Loki | scrape targets, datasource/dashboard, Loki receiver/shipper status |

**UAT host ports ตาม `.env.example`:** ClickHouse HTTP `18123` / native `19000` / metrics `19363`; MinIO API `19090` / Console `19091`; RustFS API `19094` / Console `19095` (optional); API `18000` (profile); PostgreSQL `15432`, MySQL `13306`, SQL Server `11433`, MongoDB `17017`; Redpanda Kafka `19092` / Admin `19644` / Console `18088`; Prometheus `19093`, Grafana `13000`, Loki `13100`. ค่าใน Portainer อาจ override template จึงตรวจ stack variables ก่อนใช้. พอร์ต host ต้องอยู่หลัง approved firewall/VPN; ห้ามเผยแพร่สู่ Internet เพียงเพราะคู่มือแสดงพอร์ต.

## 3. Data Sources UAT

Source stack มีฐานข้อมูลสี่ชนิดสำหรับ integration tests. เปิด **Containers** เพื่อดูสถานะ `source-postgres`, `source-mysql`, `source-mssql`, `source-mssql-init` และ `source-mongodb`; init job จบสำเร็จได้โดยไม่ต้องอยู่ในสถานะ running. ข้อมูลใน stack นี้ต้องเป็น synthetic/masked. ดู [Compose](../compose/docker-compose.datasources.yml) และ init scripts ใน [datasources/init](../datasources/init/) เพื่อทราบชื่อ database/sample schema ที่ image สร้าง.

| ระบบต้นทาง | UAT host port ตั้งต้น | Database/account จาก template | วิธีตรวจแบบ read-only |
| --- | ---: | --- | --- |
| PostgreSQL 16 | `15432` | `source_uat` / `source_app` | container health `pg_isready` แล้ว `SELECT 1` ด้วย approved client |
| MySQL 8.4 | `13306` | `source_uat` / `source_app` | container health `mysqladmin ping` แล้ว `SELECT 1` |
| SQL Server 2022 | `11433` | `source_uat` / `source_app` หลัง `source-mssql-init` สำเร็จ | health query `SELECT 1`; ตรวจ init job exit code |
| MongoDB 8 | `17017` | `source_uat` / `source_app` จาก image init | container health `ping` แล้ว read query ด้วย approved client |

วิธีเชื่อมต่อจากเครื่องที่ได้รับอนุญาต: ใช้ host/DNS และ host port จาก stack, เลือก application account เฉพาะระบบจาก secret manager, เปิด TLS ตาม network policy และทดสอบ read-only query. อย่าใช้ root/`sa` สำหรับ ingestion. [`PostgresConnector`](../ingestion/connectors/postgres_connector.py) มี watermark extraction แต่ source containers ไม่ถูกผูกเข้ากับ connector/runner อัตโนมัติ; MySQL, SQL Server และ MongoDB ยังไม่มี connector module ใน `ingestion/connectors/`. จึงต้องแยก “source container พร้อม” ออกจาก “pipeline ดึงข้อมูลแล้ว”.

[SQL Server init script](../datasources/init/init-mssql-source.sh) เพิ่ม `source_app` ใน `db_datareader` และ `db_datawriter`; [MongoDB init](../datasources/init/init-mongodb-source.js) ให้ `readWrite`. สิทธิ์เหล่านี้เป็นค่า UAT source setup ปัจจุบัน ไม่ใช่ least-privilege read-only ingestion account ตาม production policy. ก่อนเชื่อมต่อข้อมูลจริงต้องจัด account และ grants ใหม่ตามหน้าที่.

## 4. Batch ingestion และ Object Storage

[`sample_ingestion.py`](../ingestion/sample_ingestion.py) สร้าง order ตัวอย่าง 500 แถว, seed dimensions, insert `raw.orders_landing` และเติม `mart.fact_sales` จาก order ที่ไม่ถูกยกเลิก. รันซ้ำอาจเพิ่มข้อมูลซ้ำ จึงใช้เฉพาะ UAT dataset ที่ยอมรับ replay ได้. Script ยัง **ไม่มี code อัปโหลด Parquet/JSON ไป MinIO** แม้ docstring และ environment variables กล่าวถึง S3. [Connectors](../ingestion/connectors/) มี Base, PostgreSQL, REST API และ file drop; ใช้ state watermark ใน `.state/` บนเครื่องที่รัน และต้องออกแบบ idempotency/replay เพิ่มก่อนใช้จริง.

MinIO ใน Core เป็น S3-compatible UAT lake. เข้า Console ผ่าน approved host/port `19091` ด้วย credential ที่ได้รับอนุญาต แล้วตรวจ bucket ตาม `S3_BUCKET_LAKE`. `minio-init` สร้าง bucket และปิด anonymous access; การเห็น bucket ไม่พิสูจน์ว่ามี Parquet landing files. `clickhouse_data/` เป็นเส้นทาง S3 cold disk ของ ClickHouse; อย่าแก้ object ภายใต้ path นี้ด้วยมือ. [`storage_configuration.xml`](../clickhouse/config.d/storage_configuration.xml) และ [`mart.fact_sales` TTL](../sql/init/02_medallion_tables.sql) กำหนด hot-to-cold tier. Optional RustFS ต้องเปิด profile และตั้ง `CLICKHOUSE_S3_*` ให้ตรงก่อนอ้างว่าเป็น cold disk จริง.

**ตรวจแบบไม่เปลี่ยนข้อมูล:** ดู bucket/object list ผ่าน Console, query `system.disks`/`system.storage_policies` และเปรียบเทียบ endpoint/path กับ stack variables. [S3/Parquet/Iceberg DDL](../sql/init/06_lakehouse_open_formats.sql) เป็น optional migration ไม่ได้ bootstrap อัตโนมัติ; ต้องมีไฟล์/catalog, credentials และ SQL validation ก่อน apply.

## 5. Streaming: Redpanda → ClickHouse raw

1. ใน Redpanda Console (`http://<UAT_HOST_OR_DNS>:18088` ผ่าน trusted network) ตรวจ broker และ topic `enterprise.orders.events`.
2. [producer จำลอง](../streaming/kafka_producer_sim.py) ส่ง event คำสั่งซื้อไป broker; ใช้ `python streaming/kafka_producer_sim.py --help` เพื่อดู arguments ก่อนรัน. `--dry-run` ทดสอบ payload โดยไม่ส่ง broker.
3. [Kafka engine table](../sql/init/05_kafka_streaming.sql) ใช้ `redpanda:29092` และ consumer group `clickhouse_orders_consumer`; MV `raw.mv_kafka_orders_to_landing` เติม metadata แล้วเขียน `raw.orders_landing`.
4. ตรวจ consumer group/lag ใน Console และ query counts/timestamps ใน ClickHouse ก่อนและหลัง event ทดสอบ. บันทึกจำนวนส่ง/รับจริง; อย่าอ้าง “sub-second” จนกว่าจะวัด end-to-end latency.

นี่เป็น Kafka-compatible event demo, **ไม่ใช่ CDC connector ที่อ่าน transaction log จาก PostgreSQL/MySQL/SQL Server/MongoDB**. ค่า `kafka_skip_broken_messages=100` อาจข้าม payload ที่เสียรูป; ต้องมีวิธีตรวจ/replay/แจ้งเตือนที่องค์กรอนุมัติ. Broker เดียวใน UAT ไม่ใช่ HA.

## 6. ClickHouse Medallion

ClickHouse UAT ใช้ HTTP host port `18123` หรือ native `19000`; container ใช้ `8123`/`9000`. รัน SQL ด้วย read-only role เมื่อแค่ตรวจข้อมูล; `admin` ใช้เฉพาะงานที่จำเป็น. ฐานข้อมูลคือ `raw`, `core`, `mart`, `serving`. [`01–05` SQL init](../sql/init/) สร้าง tables, RBAC และ Kafka objects; optional `06` ต้อง apply แยก.

```sql
SELECT name FROM system.databases
WHERE name IN ('raw', 'core', 'mart', 'serving') ORDER BY name;

SELECT database, name, engine FROM system.tables
WHERE database IN ('raw', 'core', 'mart', 'serving')
ORDER BY database, name;

SELECT count() AS rows, max(_ingested_at) AS newest_ingestion
FROM raw.orders_landing;

SELECT sale_date, branch_id, total_orders, total_revenue
FROM serving.v_daily_branch_sales
ORDER BY sale_date DESC LIMIT 20;
```

`raw.orders_landing` เก็บข้อมูล source-aligned และ technical metadata 7 คอลัมน์; `core.dim_customer`/`dim_product` ใช้ ReplacingMergeTree สำหรับ version/tombstone; `mart.fact_sales` เป็น fact ที่มี TTL ไป cold volume; serving MV/view สรุปยอดรายวันตามสาขา. [dbt gold model](../dbt/models/gold/gold_sales_summary.sql) กับ `mart.fact_sales` เป็นคนละ object; serving view ใน SQL init อ่าน fact_sales path. CDC read ที่ต้องถูกต้องทันทีควรใช้ `FINAL`/argMax logic ตาม policy และทดสอบต้นทุน query. ตรวจ query filter, partition pruning, storage policy, active parts และ data freshness ตาม workload.

## 7. dbt Transformation

[dbt project](../dbt/dbt_project.yml) อ่าน source `raw.orders_landing` → model `silver_orders_cleaned` → `gold_sales_summary`; [tests](../dbt/tests/) ตรวจยอดขายติดลบและ [source tests](../dbt/models/bronze/sources.yml) ตรวจ not-null. `dbt-runner` เป็น on-demand profile จึงไม่ควรคาดว่าจะเห็น container running ตลอด.

ก่อนรัน ตรวจว่า image มี `dbt/profiles.yml` ที่ใช้ environment variables สำหรับ credential. Repository มีเพียง [`profiles.yml.example`](../dbt/profiles.yml.example) และตัวอย่างระบุ cluster `cluster_1s_2r` ซึ่งต้องปรับสำหรับ UAT single-node. Image ที่ publish แล้วต้องตรวจจริงว่ามี profile ที่ถูกต้อง; การ build สำเร็จไม่พิสูจน์ว่า `dbt run` ใช้งานได้.

```bash
docker compose -f compose/docker-compose.dev.yml --profile tools run --rm dbt-runner debug --profiles-dir .
docker compose -f compose/docker-compose.dev.yml --profile tools run --rm dbt-runner run --profiles-dir .
docker compose -f compose/docker-compose.dev.yml --profile tools run --rm dbt-runner test --profiles-dir .
```

คำสั่งนี้เป็นขั้นตอนสำหรับผู้ดูแลบน UAT Docker endpoint ที่มี environment/image พร้อมแล้ว; เก็บ output จริงของ `debug`, `run`, `test` และ query row count หลังรัน. อย่าใส่รหัสผ่าน literal ใน profile หรือ command history.

## 8. Serving REST API

`serving-api` อยู่ใน Core profile `api`; ตรวจว่ามี container จริงก่อนเข้า `http://<UAT_HOST_OR_DNS>:18000/docs` ผ่าน trusted network. `/health` ตรวจแค่ process ไม่ได้ query ClickHouse. [Sales router](../api/routers/sales.py) และ [Metrics router](../api/routers/metrics.py) มี endpoint ดังนี้:

| Endpoint | สิ่งที่คืน/แหล่งข้อมูล | เงื่อนไข |
| --- | --- | --- |
| `GET /health` | สถานะของ FastAPI process | ไม่พิสูจน์ ClickHouse |
| `GET /api/v1/sales/daily-summary?days=7&limit=50` | ยอดรายวันจาก `serving.v_daily_branch_sales` | `days` 1–90, `limit` 1–500 |
| `GET /api/v1/sales/branch/{branch_id}?days=30` | ยอดตามสาขาจาก serving view | `days` 1–180 |
| `GET /api/v1/sales/top-products?limit=10` | `mart.fact_sales` join `core.dim_product` | SQL role `api_user` ปัจจุบันยังไม่ grant core/mart |
| `GET /api/v1/metrics/data-quality` | รัน reconciliation เมื่อเรียก | ต้องเข้าถึง ClickHouse ได้ |
| `GET /api/v1/metrics/cluster-stats` | system tables | query `query_signal` ต้องพิสูจน์บน ClickHouse version จริง |

ทดสอบ `/health`, daily-summary และผล/HTTP status ของแต่ละ endpoint แยกกัน. API code เปิด CORS `*`; จำกัด exposure ผ่าน network/TLS/reverse proxy และ review role grants ก่อนให้ผู้ใช้งานนอกทีม. หลีกเลี่ยงการส่งรายละเอียด ClickHouse error ที่มีข้อมูลอ่อนไหวกลับ client ในระบบจริง.

## 9. BI, DBeaver, Power BI และ SQL

ผู้ใช้งาน BI ใช้ `bi_user` ที่อ่าน `mart.*`/`serving.*` ตาม [RBAC SQL](../sql/init/04_rbac_and_row_policies.sql). ใน DBeaver/ODBC/Power BI ให้ใช้ **host port ของ UAT** (`18123` HTTP หรือ `19000` Native) ไม่ใช่ container port `8123`/`9000` เมื่อเชื่อมจากภายนอก Docker network. กำหนด TLS proxy/driver/DSN ตามนโยบายองค์กรและขอ credential จาก secret manager. เริ่มด้วย `serving.v_daily_branch_sales` และ `mart.fact_sales`; จำกัดช่วงวันที่และ `LIMIT` เพื่อไม่สร้าง full scan.

```sql
SELECT sale_date, branch_id, total_orders, total_revenue
FROM serving.v_daily_branch_sales
WHERE sale_date >= today() - 14
ORDER BY sale_date DESC, branch_id
LIMIT 100;
```

ยอดขายใน UAT อาจเป็น synthetic; อย่านำไปใช้เป็นตัวเลขธุรกิจจริง. [semantic metrics](../semantics/metrics.yml) ระบุสูตร KPI ที่ควรตรวจความตรงกันกับ SQL view/dashboard ก่อนเผยแพร่รายงาน.

## 10. Observability: Prometheus, Grafana, Loki

- **Prometheus:** ผ่าน approved host port `19093` เปิด **Status > Targets** ตรวจ `clickhouse-uat` และ `minio-uat` เป็น `UP` ตาม [scrape config](../monitoring/prometheus/prometheus.uat.yml). ตรวจ **Alerts** กับ [alert_rules.yml](../monitoring/prometheus/alert_rules.yml). บาง rule อ้าง Keeper/replication/backup metrics ที่อาจไม่มีใน UAT single-node; ตรวจ expression และ datasource จริง.
- **Grafana:** ผ่าน host port `13000` เปิด dashboard ที่ provision ใน [monitoring/grafana](../monitoring/grafana/). ตรวจ datasource, time range, query และ panel data; panel ว่างไม่ได้แปลว่า ClickHouse ล้มเสมอ. ใช้ account ส่วนบุคคล/role ที่กำหนด.
- **Loki:** ผ่าน host port `13100` เป็น log backend; UAT Compose ยังไม่มี log shipper. การเห็น Loki container running ไม่ได้พิสูจน์ว่า log จาก ClickHouse/Redpanda/API ส่งเข้า Loki แล้ว. ตรวจ source/labels/query ก่อนอ้าง centralized logging.
- **FastAPI metrics endpoints** เป็น on-demand queries ไม่ใช่ Prometheus scrape configuration ของ UAT. ตรวจสิทธิ์และ latency แยกจาก native ClickHouse metrics.

สำหรับ incident ให้บันทึกเวลา, affected stack/container, alert expression, metric/query, recent change และ link [troubleshooting runbook](../runbooks/03_troubleshooting_and_failover.md). ห้ามคัดลอก logs ที่มี secret หรือ customer data ลง issue/report.

## 11. Data Quality, Contract, Catalog และ Orchestration

[orders contract](../contracts/orders_contract.yml) ระบุ schema/metadata/allowed values. [validator](../governance/validate_contract.py) เป็น CLI แยก: `--dry-run` ตรวจ sample cases, `--data-file` ตรวจ JSON file ที่ผู้ใช้ระบุ. ยังไม่ได้บังคับกับทุก ingestion path. Contract ยอมรับ `COMPLETED`/`PENDING`/`CANCELLED` แต่ sample loader ยังสร้าง `PROCESSING`/`SHIPPED` จึงต้องแก้ contract หรือ generator ก่อนเปิด gate จริง.

[Reconciliation](../data_quality/reconciliation.py) query จำนวนแถว/คุณภาพข้อมูลจาก ClickHouse; [anomaly detector](../data_quality/anomaly_detector.py) ใช้ค่าประวัติจำลองใน `run_suite()` แม้ไม่ได้ใส่ `--dry-run` จึงไม่ใช่ live alerting. [catalog generator](../scripts/generate_catalog.py) สร้าง [Data Catalog](DATA_CATALOG.md) จาก SQL DDL; ตรวจ diff ก่อน commit. [pipeline orchestrator](../orchestration/pipeline_orchestrator.py) เรียง ingestion → dbt run → dbt tests → reconciliation → backup และเขียน audit JSON ใน `orchestration/runs/`. `--dry-run` แสดงแผนโดยไม่รัน external commands; backup/reconciliation เป็น non-critical steps จึงอ่านผลทีละ step.

| งาน | ตัวอย่างคำสั่งบน approved runner | ความหมายของผล |
| --- | --- | --- |
| ตรวจ contract sample | `python governance/validate_contract.py --dry-run` | ตรวจกฎกับข้อมูลตัวอย่างเท่านั้น |
| ตรวจ contract กับไฟล์ | `python governance/validate_contract.py --data-file <TEST_JSON>` | ใช้ข้อมูล synthetic/masked |
| ตรวจ pipeline plan | `python orchestration/pipeline_orchestrator.py --dry-run` | ไม่ได้ ingest/dbt/backup จริง |
| Reconciliation จริง | `python -m data_quality.reconciliation` | ต้องตั้ง ClickHouse environment |
| สร้าง catalog | `python scripts/generate_catalog.py` | เขียน `docs/DATA_CATALOG.md` |
| ตรวจ policy | `python governance/policy_linter.py` | static policy checks บางข้อ |

## 12. AI, Semantic Search, Incident Triage และ FinOps

| เครื่องมือ | วิธีใช้/ข้อมูลที่ใช้ | ขอบเขต |
| --- | --- | --- |
| [Text-to-SQL](../ai_assistant/text_to_sql.py) | `python -m ai_assistant.text_to_sql "daily sales trend"`; เลือก SQL template จาก keywords | ไม่มี LLM call; ต้องมี BI read role และ [guardrails](../ai_assistant/guardrails.py) |
| [Vector demo](../ai_assistant/vector_search.py) | `python ai_assistant/vector_search.py "backup restore"` | hash-based in-memory embeddings; ไม่ query vector table จริง |
| [Incident triage](../ai_assistant/incident_triage.py) | `python ai_assistant/incident_triage.py --simulate TOO_MANY_PARTS` หรือ `--log-file <SANITIZED_LOG>` | signature matching/runbook suggestions; ไม่แก้ production เอง |
| [FinOps](../finops/query_cost_analyzer.py) | `python finops/query_cost_analyzer.py --dry-run --output <REPORT_PATH>` | simulation/estimated cost; live mode query `system.query_log` หากเข้าถึงได้ และ fallback simulation เมื่อไม่ได้ |
| [Semantic catalog](../semantics/metrics.yml) | ตรวจสูตร KPI/serving mappings | YAML definition; ไม่มี semantic service ที่ deploy แยก |

ก่อนแชร์ผล AI/FinOps ต้องระบุว่าเป็น live query, simulation หรือ template. Guardrails แบบ regex ไม่แทน SQL parser/RBAC. FinOps cost เป็น heuristic ไม่ใช่ cloud billing invoice.

## 13. Backup, Restore และ DR

[backup_clickhouse.sh](../scripts/backup_clickhouse.sh) ทำ `BACKUP DATABASE mart TO S3(...)`; ไม่สำรอง raw/core/serving ทั้งหมด. ค่า default UAT ของ S3 ชี้ MinIO บน host เดียว จึงยังไม่ใช่ปลายทาง DR ที่เป็นอิสระตาม policy. Script ใช้ `curl -sS` และพิมพ์ success หลัง HTTP request; ต้องตรวจ ClickHouse response, backup object, size, time และ result จริง.

[restore_test.sh](../scripts/restore_test.sh) restore `mart` ไป `drill_restore`, เทียบ row count ของ `fact_sales` แล้ว **DROP `drill_restore`**. ก่อนรันต้องยืนยันว่า namespace นี้ไม่ได้ใช้งาน, backup ID ถูกต้อง, มีพื้นที่พอ และได้รับอนุมัติสำหรับ drill. เทียบ row count อย่างเดียวไม่พิสูจน์ checksum, completeness, RPO/RTO หรือความพร้อมของ raw/core/serving. อย่ารัน script นี้บน production โดยอาศัยคู่มือ UAT.

สำหรับ UAT ให้ใช้ [Runbook 02](../runbooks/02_backup_and_restore_operations.md) จัดทำ evidence: backup ID, source/target, ClickHouse result, object metadata, restore duration, row/hash reconciliation, ผู้ตรวจและข้อผิดพลาด. RPO ≤ 1 ชั่วโมง / RTO ≤ 4 ชั่วโมงเป็น target ที่รอ business owner sign-off ตาม `AGENTS.md`; ห้ามรายงานว่าทำได้จนกว่าจะวัดจริง.

## 14. การตรวจรับ UAT และขอบเขตของผลทดสอบ

1. ตรวจ Git ref/image digest และ health ของ container ทั้ง 4 stacks.
2. ทดสอบ ClickHouse/MinIO/Prometheus/Grafana endpoints และ SQL objects ตาม [smoke_test.py](../scripts/smoke_test.py). ใช้ environment variables ที่ได้รับอนุมัติ; Python บน host **ไม่อ่าน `.env` อัตโนมัติ**.
3. ทดสอบ source read, Kafka produce/consume, dbt `debug/run/test`, API endpoint แต่ละตัว, Grafana targets/panels และ Loki log flow ตามที่เปิดใช้จริง.
4. เก็บผล data quality, query latency, backup/restore drill เฉพาะเมื่อรันจริง. [master_e2e_test.py](../scripts/master_e2e_test.py) รวม import/static/dry-run checks หลายรายการ; [Acceptance Report](ENTERPRISE_ACCEPTANCE_TEST_REPORT.md) เป็น snapshot เดิม ไม่ใช่ runtime evidence ปัจจุบัน.

```bash
python scripts/smoke_test.py
python governance/policy_linter.py
python scripts/master_e2e_test.py
```

รันคำสั่งเฉพาะเมื่อ prerequisites พร้อมและทราบผลข้างเคียง: master suite เขียนทับ acceptance report; catalog/FinOps ก็เขียนไฟล์รายงาน. เก็บ output จริงและระบุวันที่/สภาพแวดล้อม. การไม่พบ error ใน `docker compose config` เป็น syntax evidence เท่านั้น.

## 15. รอบการปฏิบัติงานและหลักฐาน

| ความถี่ | ตรวจอะไร | หลักฐานที่ต้องเก็บ |
| --- | --- | --- |
| ก่อนเริ่มงาน UAT | 4 stacks, containers, shared networks, image references | สถานะ/เวลา/Git tag หรือ SHA โดยไม่เผย secret |
| รายวัน | ClickHouse freshness/parts/storage, Redpanda consumer lag, Prometheus targets/alerts, Grafana panels | SQL/metrics summary และ incident ticket ถ้ามี |
| ทุกครั้งที่เปลี่ยน pipeline/model | Contract, dbt tests, reconciliation, API, catalog lineage | command/output, before/after counts, rollback plan |
| ทุก release UAT | CI/GHCR result, digest, Portainer Git ref, smoke tests, review record | immutable release evidence และผู้อนุมัติ |
| ตามรอบ DR ที่อนุมัติ | Backup object/restore drill/elapsed time | ผล restore จริง, row/hash comparison, RPO/RTO ที่วัด |

หากพบปัญหา ให้หยุดการเปลี่ยนแปลงที่กำลังทำ เก็บ logs/metrics ที่ sanitize แล้ว ตรวจ [Runbook 03](../runbooks/03_troubleshooting_and_failover.md) และแจ้ง owner ตาม change/incident process. ห้ามลบ volume/database หรือเปลี่ยน firewall เพื่อแก้ UAT โดยไม่มี change approval. Production promotion, destructive migrations และ credential rotation ต้องมี human sign-off.

## 16. เอกสารต่อเนื่อง

- [README](../README.md): architecture, feature inventory, workflows และ repository map
- [Operations Manual](OPERATIONS_MANUAL.md): platform preparation, access, operation, DR
- [Developer Guide](DEVELOPER_GUIDE.md): schema/dbt/connector/API development
- [UAT Architecture](architecture/UAT_ARCHITECTURE.md): stack/network/failure boundary
- [Runbook 01](../runbooks/01_portainer_git_stack_deployment.md): UAT Portainer deployment/update/rollback
- [Runbook 05](../runbooks/05_harbor_uat_registry.md) และ [Runbook 06](../runbooks/06_github_ghcr_uat.md): registry options สำหรับ UAT

## Handoff Contract

- **Scope & Sources Inspected:** ผู้ใช้แจ้งว่า UAT implemented; ภาพ Portainer Stacks, Compose, SQL, Python modules, monitoring, README และ runbooks
- **Assumptions & Decisions:** ภาพยืนยัน stack entries เท่านั้น; ใช้ placeholders สำหรับ host/DNS/secrets; UAT single host
- **Security & Operational Impact:** คู่มือเป็น read-only operational guidance; ห้ามเผย secrets และข้อมูลจริง
- **Validation Commands & Results:** ผล live checks ต้องบันทึกจาก UAT endpoint จริง; คำสั่งในหัวข้อ 14 เป็นขั้นตอนสำหรับผู้ปฏิบัติการ
- **Remaining TBDs & Residual Risks:** container health, Git ref/digests, data, dbt profile, API role, Loki shipper, backup/restore evidence และ RPO/RTO จริง
- **Human Approval Required:** review คู่มือ/ผลตรวจโดย Platform, DBA, Security และ Data Owner; production promotion ต้องผ่าน gate แยก
