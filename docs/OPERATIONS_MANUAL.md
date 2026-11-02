# คู่มือการติดตั้งและการใช้งานระบบจริง (Operations & User Manual)
## Enterprise Data Lakehouse Platform

> **เอกสารคู่มือสำหรับ**: DevOps Engineers, Platform Engineers, SRE, DBAs, และ BI/Data Analysts  
> **เกณฑ์มาตรฐานระบบ**: Ubuntu 24 LTS | ClickHouse 26.8 LTS | Portainer CE/EE | MinIO/S3 Lake | Prometheus & Grafana | ควบคุมโดย [AGENTS.md](../AGENTS.md)

> **UAT ที่ใช้งานอยู่:** ผู้ดูแลแจ้งว่าติดตั้งแล้ว และภาพ Portainer แสดง 4 stack entries. สำหรับวิธีตรวจและใช้งานทุกระบบหลังติดตั้ง ให้เริ่มที่ [คู่มือใช้งาน UAT](UAT_USER_GUIDE.md). ภาพ Stack list ไม่ยืนยัน container health, data flow หรือผล backup/restore. ส่วน Production ในเอกสารนี้เป็น target design; ใช้ [Production readiness gate](../runbooks/04_portainer_prod_deployment.md) ก่อนดำเนินการใด ๆ.

---

## สารบัญ (Table of Contents)
0. [คู่มือใช้งานทุกระบบบน UAT](UAT_USER_GUIDE.md)
1. [ข้อกำหนดระบบและสถาปัตยกรรมเครือข่าย (System & Network Requirements)](#1-ข้อกำหนดระบบและสถาปัตยกรรมเครือข่าย)
2. [การเตรียมเครื่องแม่ข่าย (Host Hardening & OS Setup)](#2-การเตรียมเครื่องแม่ข่าย)
3. [การติดตั้งสภาพแวดล้อม DEV / UAT (Single-Host Installation)](#3-การติดตั้งสภาพแวดล้อม-dev--uat)
4. [การติดตั้งสภาพแวดล้อม Production High Availability (Multi-Host HA Installation)](#4-การติดตั้งสภาพแวดล้อม-production-high-availability)
5. [การบริหารจัดการระบบผ่าน Portainer Git-backed Stacks](#5-การบริหารจัดการระบบผ่าน-portainer-git-backed-stacks)
6. [การจัดการคลังข้อมูล S3 Object Storage](#6-การจัดการคลังข้อมูล-s3-object-storage)
7. [คู่มือการเชื่อมต่อ ClickHouse สำหรับผู้ใช้งาน (Client Connection Guide)](#7-คู่มือการเชื่อมต่อ-clickhouse-สำหรับผู้ใช้งาน)
8. [การบริหารจัดการสิทธิ์ผู้ใช้งาน (RBAC & Access Control)](#8-การบริหารจัดการสิทธิ์ผู้ใช้งาน)
9. [การตรวจติดตามระบบและการจัดการ Alert (Observability & Alerting)](#9-การตรวจติดตามระบบและการจัดการ-alert)
10. [การสำรองข้อมูลและการซ้อมกู้คืนระบบฉุกเฉิน (Backup & Disaster Recovery)](#10-การสำรองข้อมูลและการซ้อมกู้คืนระบบฉุกเฉิน)
11. [คู่มือการแก้ไขปัญหาที่พบบ่อย (Troubleshooting & FAQs)](#11-คู่มือการแก้ไขปัญหาที่พบบ่อย)
12. [การบริหารจัดการ Pipeline Orchestrator (Module M06)](#12-การบริหารจัดการ-pipeline-orchestrator-module-m06)
13. [การบริหารจัดการและเฝ้าระวังระบบ Streaming & Redpanda (Module M02)](#13-การบริหารจัดการและเฝ้าระวังระบบ-streaming--redpanda-module-m02)
14. [การทดสอบโหลดและความจุระบบ (SRE Capacity & Stress Testing - M09)](#14-การทดสอบโหลดและความจุระบบ-sre-capacity--stress-testing---m09)
15. [การดูแลรักษา Data Catalog และ Lineage ใน CI/CD](#15-การดูแลรักษา-data-catalog-และ-lineage-ใน-cicd)
16. [การกำกับดูแลและติดตาม FinOps Query Cost & Quotas](#16-การกำกับดูแลและติดตาม-finops-query-cost--quotas)
17. [การบังคับใช้ Data Contracts และการรับมือกับ Schema Drift](#17-การบังคับใช้-data-contracts-และการรับมือกับ-schema-drift)
18. [ระบบวินิจฉัยปัญหาฉุกเฉินและประสาน Runbook อัตโนมัติ (AI Incident Triage)](#18-ระบบวินิจฉัยปัญหาฉุกเฉินและประสาน-runbook-อัตโนมัติ-ai-incident-triage)
19. [การตรวจรับรองความพร้อมใช้งานระดับองค์กร (Master Acceptance Certification)](#19-การตรวจรับรองความพร้อมใช้งานระดับองค์กร-master-acceptance-certification)

---

## 1. ข้อกำหนดระบบและสถาปัตยกรรมเครือข่าย

### 1.1 ข้อกำหนดฮาร์ดแวร์ขั้นต่ำ (Hardware Baseline)
| สภาพแวดล้อม | vCPU | RAM | พื้นที่จัดเก็บข้อมูล (Local Disk) | ลักษณะ Topology |
|---|---|---|---|---|
| **DEV** | 4–8 vCPU | 16–32 GB | >= 500 GB SSD | เครื่องเดียว (Single-Host) |
| **UAT** | 8–16 vCPU | 32–64 GB | 1–2 TB NVMe | เครื่องเดียว (สำหรับทำ Benchmark) |
| **PROD (ต่อโหนด)** | 16–32+ vCPU | 64–128+ GB | 2–4+ TB NVMe | 3 เครื่องแยกอิสระ (1 Shard x 2 Replicas + 3 Keeper) |

### 1.2 พอร์ตสื่อสารและกฎความปลอดภัยไฟร์วอลล์ (Network & Firewall Rules)
| พอร์ต | โปรโตคอล | การใช้งาน | การควบคุมการเข้าถึง |
|---|---|---|---|
| **8123** | TCP (HTTP) | ClickHouse HTTP Query & REST API | จำกัดเฉพาะเครือข่ายภายในที่เชื่อถือได้ |
| **9000** | TCP (Native) | ClickHouse Native Client / DBeaver / dbt | ห้ามเปิด Public, จำกัดเฉพาะแอพพลิเคชันภายใน |
| **9009** | TCP (Interserver)| ClickHouse Data Sync ระหว่าง Replica | เฉพาะระหว่างโหนด ClickHouse ด้วยกัน |
| **9181** | TCP (Keeper Client)| ClickHouse เชื่อมต่อไปยัง Keeper | เครือข่าย Backend ของคลัสเตอร์เท่านั้น |
| **9234** | TCP (Keeper Raft) | Keeper ตกลงฉันทามติ Raft Quorum | เฉพาะระหว่างโหนด Keeper ด้วยกัน |
| **9363** | TCP (Metrics) | ClickHouse Native Prometheus Scrape | เฉพาะเครื่องเซิร์ฟเวอร์ Prometheus |
| **9000/9001**| TCP | MinIO S3 API & Web Console | ภายในและทีมบริหารจัดการ |
| **9443** | TCP (HTTPS) | Portainer Admin UI | เครือข่าย VPN ผู้ดูแลระบบเท่านั้น |

---

## 2. การเตรียมเครื่องแม่ข่าย

### 2.1 การตั้งค่า OS บน Ubuntu 24 LTS
```bash
# 1. อัปเดตแพ็กเกจระบบ
sudo apt update && sudo apt upgrade -y

# 2. ตั้งค่าการซิงโครไนซ์เวลา (Time Synchronization - สำคัญมากสำหรับ ClickHouse Cluster)
sudo apt install -y chrony
sudo systemctl enable --now chrony
chronyc tracking

# 3. ตั้งค่าขีดจำกัด File Descriptors และ Virtual Memory
sudo bash -c 'cat <<EOF >> /etc/security/limits.conf
* soft nofile 262144
* hard nofile 262144
EOF'

sudo sysctl -w vm.max_map_count=1600000
echo "vm.max_map_count=1600000" | sudo tee -a /etc/sysctl.conf
```

### 2.2 การติดตั้ง Docker Engine & Compose V2
```bash
# ติดตั้ง Docker ผ่าน Official Repository
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# ตรวจสอบเวอร์ชัน
docker --version
docker compose version
```

---

## 3. การติดตั้งสภาพแวดล้อม DEV / UAT

สภาพแวดล้อม DEV/UAT แบ่งเป็น 4 Portainer stacks บน host เดียว. หากติดตั้ง UAT แล้ว ให้ใช้ [คู่มือ UAT หัวข้อ Portainer](UAT_USER_GUIDE.md#2-ตรวจสถานะและเข้าใช้งาน-4-portainer-stacks) ตรวจ Git ref, containers, networks และ endpoints; ขั้นตอนด้านล่างเป็นตัวอย่างการเตรียม host ใหม่. ก่อนรันต้องสร้าง external networks `lakehouse-uat-integration` และ `lakehouse-uat-observability`, ตั้ง credentials และเตรียม custom images ตาม [Runbook 01](../runbooks/01_portainer_git_stack_deployment.md).

```bash
# 1. Clone repository
git clone https://github.com/kingpac-dev/Enterprise-Data-Lakehouse-Platform.git
cd Enterprise-Data-Lakehouse-Platform

# 2. คัดลอกและกำหนดรหัสผ่านในไฟล์ .env
cp .env.example .env
nano .env

# 3. เริ่มเฉพาะ Core Stack หลังเตรียม networks/images
docker compose -f compose/docker-compose.dev.yml up -d

# 4. ตรวจ Core containers; source/streaming/observability เป็นคนละ Compose
docker compose -f compose/docker-compose.dev.yml ps
```

ทดสอบการเชื่อมต่อ ClickHouse:
```bash
curl -s http://localhost:18123/ping
# ผลที่คาด: Ok. เมื่อ endpoint พร้อมจริง
```

---

## 4. การติดตั้งสภาพแวดล้อม Production High Availability

> [!CAUTION]
> Production ยังเป็น **NOT READY FOR PRODUCTION** ตาม [Runbook 04](../runbooks/04_portainer_prod_deployment.md). คู่มือ UAT นี้ไม่ใช่คำสั่ง deploy Production. ต้องมีอย่างน้อย 3 failure domains ที่แยกกัน, Keeper quorum, ClickHouse 2 replicas, independent S3, approved secrets/network/TLS, image patch/digest และหลักฐาน load/failover/restore พร้อม human sign-off ก่อน promotion.

ดู [Production Architecture](architecture/PROD_ARCHITECTURE.md) สำหรับ topology เป้าหมาย และ [Runbook 04](../runbooks/04_portainer_prod_deployment.md) สำหรับ blocking gaps, network matrix, ลำดับตรวจและ approval gates. ค่า host IP/DNS, load balancer, enterprise S3, KMS, RPO/RTO ที่อนุมัติ และข้อมูลองค์กรอื่น ๆ ยังเป็น **TBD**; ไม่ใช้ IP ตัวอย่างหรือ UAT Compose เป็น Production configuration.

---

## 5. การบริหารจัดการระบบผ่าน Portainer Git-backed Stacks

การควบคุมการปล่อยเวอร์ชัน (Deployment) ในระดับองค์กรจะดำเนินการผ่าน **Portainer Git-backed Stacks** เพื่อป้องกันการแก้ไขคอนฟิกแบบ Ad-hoc ที่ไม่ผ่านการตรวจสอบ:

สำหรับ UAT ที่ติดตั้งแล้ว ให้เริ่มจาก [คู่มือ UAT](UAT_USER_GUIDE.md#2-ตรวจสถานะและเข้าใช้งาน-4-portainer-stacks) เพื่อตรวจ 4 stack entries, container health, Git reference และ image digest. ขั้นตอนด้านล่างใช้กับการสร้างหรืออัปเดต stack ตาม change record โดยผู้มีสิทธิ์เท่านั้น; อย่า redeploy เพียงเพื่อดูสถานะ.

1. เข้าสู่หน้าเว็บ Portainer: `https://<portainer-host>:9443`
2. เลือก Environment -> ไปที่เมนู **Stacks** -> กดปุ่ม **Add stack**
3. เลือกหัวข้อ **Repository**:
   - **Repository URL**: `https://github.com/kingpac-dev/Enterprise-Data-Lakehouse-Platform.git`
   - **Repository reference**: approved immutable tag/SHA สำหรับ release นั้น
   - **Compose path (UAT)**: `compose/docker-compose.dev.yml`, `compose/docker-compose.datasources.yml`, `compose/docker-compose.streaming.yml` หรือ `compose/docker-compose.observability.yml` ตาม stack
4. ในส่วน **Environment variables**: เพิ่มตัวแปรความลับที่กำหนดไว้ใน `.env.example`
5. เปิดใช้งาน **GitOps updates** (Webhook หรือ Polling)
6. กด **Deploy the stack**

---

## 6. การจัดการคลังข้อมูล S3 Object Storage

ค่า template ของ UAT ใช้ bucket `enterprise-data-lake`; โครงสร้างด้านล่างเป็น **target path convention** ไม่ได้ยืนยันว่าทุก prefix มี object แล้ว. ตรวจรายการจริงใน MinIO Console ก่อนอ้างข้อมูล:
```text
enterprise-data-lake/
├── landing/              # ข้อมูลดิบที่รับเข้าจาก API / Batch (Immutable)
│   └── orders/YYYY/MM/DD/
├── bronze/               # ข้อมูลระดับ Bronze ที่ถูกจัดเก็บในรูป Apache Parquet
├── archive/              # ข้อมูลประวัติศาสตร์ระยะยาว
├── backup/               # ไฟล์สำรองข้อมูล Native Backup ของ ClickHouse
│   └── clickhouse/
└── clickhouse_data/      # พื้นที่จัดเก็บสำหรับตาราง Cold Tier ของ ClickHouse
```

---

## 7. คู่มือการเชื่อมต่อ ClickHouse สำหรับผู้ใช้งาน

### 7.1 การเชื่อมต่อผ่าน DBeaver (สำหรับ Data Engineers & Analysts)
1. เปิดโปรแกรม DBeaver -> New Database Connection -> เลือก **ClickHouse**
2. ตั้งค่า Connection:
   - **Host**: `<clickhouse-host-ip>`
   - **Port จากภายนอก UAT Docker host**: `18123` (HTTP Driver) หรือ `19000` (Native Driver) ตามค่า Portainer environment; `8123`/`9000` เป็น container ports
   - **Database**: `mart` หรือ `serving`
   - **Username**: `bi_user` (สำหรับ BI) หรือ `admin`
   - **Password**: ตามที่กำหนดใน `.env`

### 7.2 การเชื่อมต่อผ่าน Python (`clickhouse-connect`)
```python
import clickhouse_connect

client = clickhouse_connect.get_client(
    host='localhost',
    port=18123,
    username='bi_user',
    password='<password>',
    database='serving'
)

df = client.query_df('SELECT * FROM serving.v_daily_branch_sales LIMIT 100')
print(df.head())
```

### 7.3 การเชื่อมต่อผ่าน Power BI Desktop
1. ใน Power BI Desktop เลือก **Get Data** -> ค้นหา **ODBC** หรือใช้ **ClickHouse Connector** จาก AppSource
2. กำหนด Connection String หรือ DSN ชี้ไปยัง UAT host port `18123` (หรือ approved TLS proxy) ไม่ใช่ container port `8123`
3. เลือก Database `serving` เพื่อดึงข้อมูลจาก Materialized Views

### 7.4 การให้บริการผ่าน Serving REST API Microservice (FastAPI)
ระบบมีไมโครเซอร์วิส FastAPI สำหรับให้บริการข้อมูล Serving Layer แก่ Application ภายนอกใน [api/](../api):
- **เปิดใช้งาน Service**:
  ```bash
  # Linux / macOS:
  ./scripts/manage.sh api-start

  # Windows:
  .\scripts\manage.ps1 api-start
  ```
- **OpenAPI Interactive Docs**: `http://<host>:18000/docs`
- **Endpoints หลัก**:
  - `GET /api/v1/sales/daily-summary?days=7`: ดึงยอดขายสรุปรายวันจาก Serving View; latency ต้องวัดจริงก่อนอ้างระดับ Sub-second
  - `GET /api/v1/sales/branch/{branch_id}`: ประสิทธิภาพยอดขายตามสาขา
  - `GET /api/v1/sales/top-products`: สินค้าขายดี 10 อันดับแรก
  - `GET /api/v1/metrics/data-quality`: ผลการกระทบยอด Data Quality ล่าสุด

> [!IMPORTANT]
> API profile `api` ไม่ได้รันโดยอัตโนมัติพร้อม Core. `/health` ตรวจเฉพาะ process; `/top-products` อ่าน `mart`/`core` แต่ role `api_user` ใน SQL init grant เฉพาะ `serving.*` จึงต้อง review สิทธิ์และทดสอบจริงก่อนเปิด endpoint.

---

## 8. การบริหารจัดการสิทธิ์ผู้ใช้งาน


ระบบกำหนด Role และ Profile ไว้อย่างชัดเจนตามหลัก Least Privilege ใน [sql/init/04_rbac_and_row_policies.sql](../sql/init/04_rbac_and_row_policies.sql):

| บัญชีผู้ใช้ | Role | สิทธิ์การเข้าถึง | โควตาและข้อจำกัด |
|---|---|---|---|
| `admin` | `role_platform_admin` | สิทธิ์สูงสุดในคลัสเตอร์ | ไม่จำกัดโควตา |
| `etl_user` | `role_etl_service` | `INSERT`, `SELECT` บน `raw.*`, อ่าน `core.*` | เปิดใช้งาน `async_insert`, จำกัดแรม 16GB |
| `bi_user` | `role_bi_readonly` | `SELECT` บน `mart.*` และ `serving.*` เท่านั้น | ห้ามแก้ข้อมูล, Timeout 60 วิ, โควตา 1,000 QPH |
| `api_user` | `role_api_service` | `SELECT` บน `serving.*` เท่านั้น | Timeout 10 วิ, จำกัดแรม 2GB, โควตา 10,000 QPH |
| `monitoring_user`| `role_monitoring_service` | `SELECT` บน `system.*` เท่านั้น | สำหรับ Prometheus ดึงเมทริกซ์ |

---

## 9. การตรวจติดตามระบบและการจัดการ Alert

### 9.1 แดชบอร์ด Grafana
เข้าใช้งานผ่าน UAT host port `http://<UAT_HOST_OR_DNS>:13000` (หรือ approved TLS proxy) -> ตรวจ dashboard ที่ provision ตาม [Grafana config](../monitoring/grafana/). Port `3000` เป็นพอร์ตภายใน container:
- ตรวจสอบ Throughput อัตราการรัน Query (QPS)
- ตรวจสอบ Memory Tracking ของแต่ละโหนด
- ตรวจสอบจำนวน Active Parts ของตารางใน MergeTree

### 9.2 การรับมือเมื่อเกิด Alert (ตามที่กำหนดใน [monitoring/prometheus/alert_rules.yml](../monitoring/prometheus/alert_rules.yml))
1. **`ClickHouseHighQueryErrors`**: เกิด Query ผิดพลาดสูง
   - ตรวจสอบ `system.query_log` เพื่อหาคำสั่งที่ Error หรือ Syntax ผิด
2. **`ClickHousePartsExplosion`** (>300 active parts):
   - มีการยิงคำสั่ง Insert ขนาดเล็กถี่เกินไป (Micro-batching)
   - ตรวจ batch size/`async_insert = 1` ที่ตัวส่งข้อมูล; `OPTIMIZE TABLE ... FINAL` กระทบ I/O สูงและต้องให้ DBA review ก่อนใช้
3. **`ClickHouseReplicationQueueLag`**: การ Sync ระหว่างโหนดล่าช้า
   - ตรวจสอบการเชื่อมต่อเครือข่ายระหว่างโหนด ClickHouse และตรวจสอบสุขภาพของ Keeper

---

## 10. การสำรองข้อมูลและการซ้อมกู้คืนระบบฉุกเฉิน

### 10.1 การสำรองข้อมูลอัตโนมัติ (Automated Backup)
มีสคริปต์ [scripts/backup_clickhouse.sh](../scripts/backup_clickhouse.sh) สำหรับ `BACKUP DATABASE mart TO S3`. การมีสคริปต์ไม่ได้แปลว่ามี schedule หรือ backup สำเร็จแล้ว; UAT default ใช้ MinIO บน host เดียวซึ่งไม่ใช่ independent DR destination. ตรวจผล SQL/HTTP และ object จริงตาม [คู่มือ UAT](UAT_USER_GUIDE.md#13-backup-restore-และ-dr) ก่อนบันทึกว่าสำเร็จ:
```bash
./scripts/manage.sh backup
```

### 10.2 การซ้อมกู้คืนระบบฉุกเฉิน (Non-Destructive DR Drill)
รอบการซ้อมต้องกำหนดตามนโยบายองค์กร; **RPO <= 1 ชั่วโมง** และ **RTO <= 4 ชั่วโมง** เป็น target รอ business owner sign-off และต้องวัดจริง:
```bash
./scripts/manage.sh restore-drill <backup_id>
```
สคริปต์ restore `mart` ไป `drill_restore`, เทียบจำนวนแถวของ `fact_sales` และจับเวลาขั้น restore จากนั้นสั่ง `DROP DATABASE drill_restore`. **ไม่ได้เทียบ checksum** และชื่อ database drill เป็นค่าคงที่; ยืนยันว่าชื่อนี้ว่าง/แยกเฉพาะ drill ก่อนรัน. ห้ามใช้ script UAT นี้บน Production โดยไม่มีขั้นตอนและการอนุมัติแยก.

---

## 11. คู่มือการแก้ไขปัญหาที่พบบ่อย

### Q1: ClickHouse ขึ้นสถานะ Read-Only Table เกิดจากอะไร?
หัวข้อนี้ใช้กับ replicated production target; UAT single-node ตาม Compose ปัจจุบันไม่มี Keeper quorum ให้ failover.
**สาเหตุ**: ClickHouse ไม่สามารถติดต่อกับ ClickHouse Keeper ได้ หรือ Keeper สูญเสียเสียงส่วนใหญ่ใน Raft Quorum (มี Keeper รอดน้อยกว่า 2 ใน 3 โหนด)  
**วิธีตรวจใน production ที่อนุมัติแล้ว**: ตรวจ `system.replicas`, Keeper quorum, network และ logs ตาม [Runbook 03](../runbooks/03_troubleshooting_and_failover.md). การ restart Keeper ต้องอยู่ใน incident/change process; ไม่ให้ทำจาก UAT guide นี้.

### Q2: อาการ "Too many parts in all data parts in table" แก้ไขอย่างไร?
**สาเหตุ**: มีการบันทึกข้อมูลแบบแถวเดี่ยวๆ เข้ามาด้วยความถี่สูงเกินกว่าที่ Background Merge ของ ClickHouse จะรวมไฟล์ทัน  
**วิธีแก้ไข**: 
1. รวมข้อมูลเป็นก้อน (Batch Size >= 1,000 แถว หรือทุก 1-5 วินาที) ก่อนส่งเข้ามา
2. เปิดใช้งานการรวมก้อนฝั่งเซิร์ฟเวอร์โดยส่ง Header `X-ClickHouse-Setting: async_insert=1,wait_for_async_insert=1`

---

## 12. การบริหารจัดการ Pipeline Orchestrator (Module M06)

### 12.1 การตรวจสอบสถานะการทำงานของ Pipeline
Orchestrator บันทึกประวัติการรันและสถานะของแต่ละขั้นตอนลงในไดเรกทอรี `orchestration/runs/`:
```bash
# ตรวจสอบประวัติการรันล่าสุด
ls -lt orchestration/runs/ | head -n 5

# ดูรายละเอียดผลการรัน
cat orchestration/runs/<run_id>.json
```

### 12.2 การตั้งเวลาทำงานอัตโนมัติ (Cron / Systemd Timer)
ตัวอย่างสำหรับเครื่องที่ไม่ได้ใช้ Airflow; repository ไม่ได้ติดตั้ง cron job นี้ให้. ต้องเตรียม environment/secrets, output retention, monitoring และอนุมัติ schedule ก่อนสร้าง `/etc/cron.d/lakehouse-daily`:
```cron
# รัน Pipeline ประจำวันเวลา 02:00 น. UTC; webhook ต้องกำหนดแยก
0 2 * * * root cd /opt/Enterprise-Data-Lakehouse-Platform && ./scripts/manage.sh run-pipeline >> /var/log/lakehouse-pipeline.log 2>&1
```

---

## 13. การบริหารจัดการและเฝ้าระวังระบบ Streaming & Redpanda (Module M02)

### 13.1 การตรวจสอบสถานะ Redpanda Cluster
```bash
# ตรวจสอบสถานะคลัสเตอร์ Redpanda ผ่าน Docker
docker exec -it lakehouse-redpanda rpk cluster health

# ดูรายการ Topic ทั้งหมด
docker exec -it lakehouse-redpanda rpk topic list

# ตรวจสอบ Consumer Group Lag ของ ClickHouse
docker exec -it lakehouse-redpanda rpk group describe clickhouse_orders_consumer
```

### 13.2 การแก้ไขปัญหา Kafka Consumer Lag
หากพบว่า Lag สะสมสูงขึ้นผิดปกติ:
1. ตรวจสอบว่า ClickHouse ทำงานปกติหรือไม่: `curl http://localhost:18123/ping`
2. ตรวจสอบข้อความผิดพลาดใน ClickHouse log: `docker logs lakehouse-clickhouse-dev | grep -i kafka`
3. หากมีข้อความผิดรูปแบบ (Corrupted JSON) ClickHouse จะข้ามอัตโนมัติตามการตั้งค่า `kafka_skip_broken_messages = 100`

---

## 14. การทดสอบโหลดและความจุระบบ (SRE Capacity & Stress Testing - M09)

ก่อนขึ้นระบบ Production หรือเมื่อมีการขยายขนาดข้อมูล ต้องรันการทดสอบโหลดแบบหลายผู้ใช้งานพร้อมกัน:
```bash
# ทดสอบโหลด 25 concurrent analytical users:
./scripts/manage.sh stress-test --concurrency 25 --requests 10

# ตัวเลขต่อไปนี้เป็นเกณฑ์ตัวอย่าง; ต้องอนุมัติและวัดกับ UAT workload จริง:
# - Throughput (QPS) > 100
# - Latency P95 <= 300 ms
# - Error Rate = 0.0%
```

---

## 15. การดูแลรักษา Data Catalog และ Lineage ใน CI/CD

Data Catalog ที่ [docs/DATA_CATALOG.md](DATA_CATALOG.md) เป็นเอกสารที่ต้องตรวจ diff เมื่อเปลี่ยน DDL หรือ dbt Model:
```bash
# อัปเดตผัง Lineage และพจนานุกรมข้อมูลก่อนทำ Pull Request
./scripts/manage.sh generate-catalog
```
CI ปัจจุบันใน [`ci.yml`](../.github/workflows/ci.yml) ยังไม่ได้รัน catalog generator; ผู้พัฒนาต้องรันและ review diff ก่อน commit หรือเพิ่ม CI gate ที่ผ่าน review.

---

## 16. การกำกับดูแลและติดตาม FinOps Query Cost & Quotas

### 16.1 การตรวจสอบการใช้ทรัพยากรรายสัปดาห์
ทีม SRE และ Data Platform ต้องตรวจสอบรายงาน FinOps อย่างน้อยสัปดาห์ละ 1 ครั้ง:
```bash
./scripts/manage.sh finops-report
```
ค่า default ของ analyzer ใช้ `localhost:8123` และหาก live query ไม่ได้จะ fallback เป็น simulation; สำหรับ UAT host ให้ระบุ `--port 18123`, account ที่อ่าน `system.query_log` ได้ และตรวจใน report ว่ามาจาก live data. ตัวเลข cost เป็น estimation ไม่ใช่ค่า billing จริง.
ตรวจสอบ 3 จุดสำคัญ:
1. **Unpartitioned Scans**: ค้นหา Query ที่สแกนข้อมูลเกิน 100 GB ในตาราง `fact_sales` โดยไม่มีเงื่อนไข `sale_date`
2. **Memory Outliers**: ผู้ใช้หรือ Service ใดใช้หน่วยความจำเกิน 4 GB บ่อยครั้ง
3. **Cost Share**: สัดส่วนต้นทุนของแต่ละบทบาทผู้ใช้ หากฝ่ายใดมีสัดส่วนเกินงบประมาณ ให้ส่งข้อมูลเพื่อทำการปรับปรุงโค้ด Query

---

## 17. การบังคับใช้ Data Contracts และการรับมือกับ Schema Drift

### 17.1 Pre-Ingestion Guard
ควรตรวจข้อมูลก่อนนำเข้าเทียบ [contracts/orders_contract.yml](../contracts/orders_contract.yml) แต่ validator ปัจจุบันเป็น CLI แยกและ **ยังไม่ได้บังคับกับ Batch/Streaming ทุก path**. คำสั่งไม่ใส่ `--data-file` จะทดสอบ sample cases เท่านั้น:
```bash
./scripts/manage.sh contract-validate
```

### 17.2 ขั้นตอนเมื่อเกิด Contract Violation
1. หากพบข้อความ `[PASS - BLOCKED] Successfully intercepted contract violations`:
   - หมายถึง validator ปฏิเสธ sample record ที่ผิดตามกฎใน process ทดสอบ; ยังไม่มี quarantine storage หรือ Slack alert ที่ต่อเข้ากับทุก ingestion path
   - ให้ผู้ดูแลหยุด job ที่เกี่ยวข้อง ตรวจ payload ที่ sanitize แล้ว และบันทึก issue ให้ Data Owner
2. หากเป็นการเปลี่ยนแปลงโครงสร้างที่ได้รับความเห็นชอบแล้ว (Approved Schema Evolution):
    - ทีม Data Engineer ต้องทำการอัปเดตเวอร์ชันของ Data Contract ใน `contracts/orders_contract.yml` (เช่น ขยับจาก `1.0.0` ไป `1.1.0`)
    - แก้ไข DDL ของ ClickHouse และ dbt models ให้สอดคล้องกัน ก่อนจะปล่อยให้ข้อมูลใหม่ไหลเข้าสู่ระบบ

---

## 18. ระบบวินิจฉัยปัญหาฉุกเฉินและประสาน Runbook อัตโนมัติ (AI Incident Triage)

เมื่อระบบตรวจพบ Alert จาก Prometheus หรือพบข้อผิดพลาดใน Server Log ทีม SRE และผู้ดูแลระบบสามารถใช้เครื่องมือวิเคราะห์อัตโนมัติ [ai_assistant/incident_triage.py](../ai_assistant/incident_triage.py) เพื่อค้นหาสาเหตุรากเหง้า (Root Cause Analysis) และขั้นตอนการแก้ไขอย่างรวดเร็ว:

### 18.1 คุณสมบัติเด่น
- **Zero-Trust Log Sanitization**: ตัดรหัสผ่าน, IP addresses, และ Connection Strings ออกจาก Log อัตโนมัติ
- **Signature Pattern Matching**: จำแนกประเภทความผิดพลาด เช่น:
  - `TOO_MANY_PARTS (Code 252)`: การเขียนข้อมูลแบบ Micro-batching ถี่เกินไป
  - `TABLE_IS_READ_ONLY (Code 242)`: ClickHouse Keeper สูญเสีย Raft Quorum หรือ Session ขาดหาย
  - `MEMORY_LIMIT_EXCEEDED (Code 241)`: Query ขนาดใหญ่ใช้หน่วยความจำเกิน Quota
  - `REPLICATION_LAG`: คิวการถ่ายโอนข้อมูลระหว่างโหนดช้าผิดปกติ
- **Runbook Suggestions**: แสดงแนวทาง/ลิงก์ไปยัง [runbooks/](../runbooks/) เพื่อให้ผู้ดูแลตรวจและตัดสินใจ; CLI ไม่แก้ปัญหาในระบบโดยอัตโนมัติ

### 18.2 คำสั่งการใช้งาน
```bash
# ตรวจสอบไฟล์ Log ที่มีปัญหา
./scripts/manage.sh triage --log-file /path/to/clickhouse-server.err.log

# ทดสอบจำลองสถานการณ์เหตุการณ์ฉุกเฉิน (Simulation Mode)
./scripts/manage.sh triage --simulate TABLE_IS_READ_ONLY

# บน Windows PowerShell:
.\scripts\manage.ps1 triage --simulate TOO_MANY_PARTS
```

---

## 19. การตรวจรับรองความพร้อมใช้งานระดับองค์กร (Master Acceptance Certification)

ใช้ [scripts/master_e2e_test.py](../scripts/master_e2e_test.py) เป็น static/dry-run regression suite สำหรับ M01–M12 ใน UAT. หลายข้อทดสอบเพียง import, การมีไฟล์ หรือ simulation; ผลผ่านไม่แทน live integration, DR drill หรือ Production readiness gate:

### 19.1 โมดูลที่ได้รับการตรวจสอบ (Acceptance Scope)
1. **[M01] Source Connectivity**: ความพร้อมของ Connector (Postgres, S3 FileDrop, REST API, Base State)
2. **[M02] Real-Time CDC & Streaming**: Redpanda Broker, Producer จำลอง และ Kafka Engine Materialized View
3. **[M03] Durable Data Lake Storage**: External S3 Parquet Landing/Archive DDL และ Apache Iceberg Engine
4. **[M04] Analytical Storage**: ฐานข้อมูล Medallion, MergeTree, Storage Tiering XML และ Keeper Quorum
5. **[M05] Transformation & Quality**: dbt-clickhouse, Data Reconciliation และ Anomaly Detection
6. **[M06] Pipeline Orchestration**: Master Orchestrator DAG พร้อม Retry, Audit Logs และ Airflow DAG
7. **[M07] Governed Serving REST API**: FastAPI Serving Microservice, Endpoints และ Swagger Documentation
8. **[M08] Data Governance & Contracts**: Open Data Contract Standard (ODCS) และ Data Catalog Generator
9. **[M09] SRE Observability & Stress Testing**: Prometheus Alerts, Grafana Dashboard และ Concurrency Benchmark
10. **[M10] DevOps & Policy-as-Code**: Docker Compose Configs, GitHub CI Workflow และ AGENTS.md Linter
11. **[M11] Backup & Disaster Recovery**: S3 Native Backup Script, Non-destructive Restore Drill และ Runbook
12. **[M12] Governed AI & Semantic Layer**: Semantic Metrics Catalog, NL-to-SQL Guardrails และ Vector Search

### 19.2 การสั่งรันและผลลัพธ์
```bash
# รันการตรวจรับรอง
./scripts/manage.sh master-test

# บน Windows PowerShell:
.\scripts\manage.ps1 master-test
```
Script เขียนทับ **[docs/ENTERPRISE_ACCEPTANCE_TEST_REPORT.md](ENTERPRISE_ACCEPTANCE_TEST_REPORT.md)** ด้วยผลรอบที่รัน. เก็บ output วันที่/environment และแยกหลักฐาน live health, data quality, load, backup/restore และ security review ก่อน sign-off.
