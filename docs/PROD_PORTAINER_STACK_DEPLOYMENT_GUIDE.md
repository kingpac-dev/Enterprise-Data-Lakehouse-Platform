# คู่มือติดตั้งและตั้งค่า Data Lakehouse Platform — PROD บน Portainer Stack

**ปรับปรุง: 2026-11-03 · สถานะ: คู่มือปฏิบัติและตรวจรับ; repository ยังไม่พร้อมสำหรับ production promotion**

> [!CAUTION]
> [AGENTS.md](../AGENTS.md) เป็นนโยบายหลัก: ระบบบน host เดียวจัดเป็น DEV/UAT แม้ artifact จะใช้ชื่อ `prod-single`; ห้ามเรียกว่า production HA หรือเปิดรับ production traffic. Production HA ต้องมีอย่างน้อย 3 failure domains, ClickHouse 2 replicas และ Keeper 3 members. การ deploy และ production promotion ต้องได้รับ human sign-off. คู่มือนี้ไม่ใช่การอนุมัติ deploy.

## สารบัญ

1. [ภาพรวมสถาปัตยกรรม](#1-ภาพรวมสถาปัตยกรรม)
2. [ข้อกำหนดเบื้องต้น](#2-ข้อกำหนดเบื้องต้น)
3. [การเตรียม Host](#3-การเตรียม-host)
4. [การ Build และ Push Image](#4-การ-build-และ-push-image)
5. [การติดตั้ง Portainer Management Plane](#5-การติดตั้ง-portainer-management-plane)
6. [การจัดการ Secrets และ Environment Variables](#6-การจัดการ-secrets-และ-environment-variables)
7. [เส้นทาง A — PROD Single Node (ไม่มี HA)](#7-เส้นทาง-a--prod-single-node-ไม่มี-ha)
8. [เส้นทาง B — PROD Multi-Host HA (3 Failure Domains)](#8-เส้นทาง-b--prod-multi-host-ha-3-failure-domains)
9. [การตรวจรับหลังติดตั้ง](#9-การตรวจรับหลังติดตั้ง)
10. [Backup, Restore และ DR](#10-backup-restore-และ-dr)
11. [Monitoring และ Observability](#11-monitoring-และ-observability)
12. [Day-2 Operations](#12-day-2-operations)
13. [Rollback Procedures](#13-rollback-procedures)
14. [Production Readiness Gate Checklist](#14-production-readiness-gate-checklist)
15. [Handoff Contract](#15-handoff-contract)

## 1. ภาพรวมสถาปัตยกรรม

| เส้นทาง | Artifact | ขอบเขตและสถานะ |
| --- | --- | --- |
| A: 1 host | [Compose single](../compose/docker-compose.prod-single.yml), [Dockerfile](../clickhouse/Dockerfile.prod-single), [preflight](../scripts/validate_prod_single_env.py) | ClickHouse 1 instance, named volumes, enterprise S3 cold disk; ไม่มี Keeper/replication. ตามนโยบายยังเป็น DEV/UAT |
| B: 3 failure domains | [Node 01](../compose/docker-compose.prod-node1.yml), [Node 02](../compose/docker-compose.prod-node2.yml), [Keeper 03](../compose/docker-compose.prod-keeper3.yml) | เป้าหมาย 1 shard × 2 replicas + 3 Keeper; **ยัง deploy เป็น PROD ไม่ได้** จนปิด P0 และทดสอบข้าม host |

Portainer ต้องใช้ Git-backed stacks จาก immutable Git release tag/SHA ที่อนุมัติ ห้ามแก้ stack แบบ ad hoc. Bridge networks ใน Compose เป็นเครือข่ายเฉพาะ host; ชื่อเดียวกันบนต่าง host ไม่ได้สร้าง overlay network. Data path ที่ต้องตรวจรับคือ source → S3/Parquet → `raw` → `core` → `mart` → `serving`; Compose ปัจจุบันยังไม่ใช่ platform ครบวงจร. ดู [architecture](architecture/PROD_ARCHITECTURE.md), [คู่มือ single-node](PROD_SINGLE_NODE_INSTALLATION_GUIDE.md), [คู่มือ multi-host](PROD_INSTALLATION_AND_OPERATIONS_GUIDE.md) และ [P0/P1 worklist](PRODUCTION_READINESS_SPECIALIST_WORKLIST.md).

## 2. ข้อกำหนดเบื้องต้น

เปิด change record และระบุเจ้าของหลักฐานก่อนเริ่ม; ค่าเฉพาะองค์กรที่ยังไม่ทราบให้ใช้ `TBD` จนอนุมัติจริง.

| รายการที่ต้องมี | หลักฐาน/ผู้อนุมัติ |
| --- | --- |
| Git SHA, image digest, SBOM/scan result, registry access | Release/CAB และ Security; ทุก node ต้องใช้ release ชุดเดียวกัน |
| Host, CPU/RAM/IOPS/capacity, Docker Root Dir, NTP, OS hardening | Platform/SRE; Ubuntu 24 LTS, Docker Engine + Compose V2 |
| Private IP, DNS, routes, source CIDR, TLS/CA, firewall tests | Network/Security; ห้ามเปิด ClickHouse/Keeper/Portainer สู่ Internet |
| Enterprise S3 cold storage และ independent S3 backup destination | Storage/Data Owner; endpoint, bucket/prefix, IAM/KMS, retention และ restore access |
| Secret delivery, RBAC, Portainer SSO/MFA, audit/backup | Security/Platform; ไม่มี secret ใน Git, Compose หรือ log |
| RPO/RTO, acceptance workload, change window, rollback owner | Business/Data Owner และ CAB; ค่าเป้าหมายยัง `TBD` จนลงนาม |

สำหรับ 3-node เพิ่ม independent failure domains ทั้ง 3, staged Git-backed Keeper/ClickHouse deployment, replicated DDL และ host-loss/rejoin test. [รายการ P0](PRODUCTION_READINESS_SPECIALIST_WORKLIST.md) ต้องมีผู้ตรวจทานแยกจากผู้จัดทำ.

## 3. การเตรียม Host

ให้ผู้ดูแลที่ได้รับอนุมัติรันคำสั่ง **อ่านสถานะ** บนแต่ละ host และเก็บผลแบบ redacted ใน change record:

```bash
hostnamectl
timedatectl status
ip -br addr
ip route
resolvectl status
lsblk -f
df -h
free -h
nproc
docker version
docker compose version
docker info --format '{{.DockerRootDir}}'
```

ตรวจว่า hostname/IP/DNS ตรง network matrix, เวลาซิงก์, filesystem และ Docker data root มี headroom ตาม sizing ที่อนุมัติ. ภาพ console ของ Node 01 ใน [คู่มือ single-node](PROD_SINGLE_NODE_INSTALLATION_GUIDE.md) แสดงเพียง boot ถึง login prompt; ไม่ใช่ผล preflight หรือหลักฐานว่า Docker/SSH/S3 พร้อม. การติดตั้ง Docker/Portainer, การแก้ LVM, firewall หรือ SSH policy ให้ทำภายใต้ change ที่อนุมัติ.

| Port | ปลายทาง | Source ที่ยอมรับ |
| --- | --- | --- |
| 8123, 9000 | ClickHouse HTTP/native | trusted API/ETL/BI/proxy ภายในเท่านั้น |
| 9363 | ClickHouse metrics | Prometheus ภายในเท่านั้น |
| 9009 | ClickHouse interserver ในเส้นทาง B | ClickHouse peers เท่านั้น |
| 9181, 9234 | Keeper client/Raft ในเส้นทาง B | cluster peers เท่านั้น |
| 9001 | Portainer Agent หากติดตั้งแยก | Portainer Server ใน management zone เท่านั้น |
| 9443 | Portainer UI | management VPN/admin เท่านั้น |

Compose bind published ports กับ `PROD_BIND_IP` หรือ `HOST_NODE*_IP` แต่ **ไม่ตรวจ** ว่า IP เป็น interface จริงหรือ firewall จำกัด source. ให้ Network owner ทดสอบจาก source ที่อนุญาตและที่ไม่อนุญาต; UFW rule เพียงอย่างเดียวไม่ใช่หลักฐาน Docker NAT. S3 egress ต้องใช้ HTTPS/CA ที่อนุมัติ. ดู [port matrix ของ multi-host](PROD_INSTALLATION_AND_OPERATIONS_GUIDE.md).

## 4. การ Build และ Push Image

สำหรับเส้นทาง A ใช้ [publish-prod-images.yml](../.github/workflows/publish-prod-images.yml): `workflow_dispatch` จาก default branch, tag ใหม่รูปแบบ `prod-v<major>.<minor>.<patch>`, build จาก Dockerfile.prod-single, smoke test กับ MinIO ชั่วคราว, Trivy HIGH/CRITICAL gate แล้ว push `ghcr.io/<GITHUB_OWNER_LOWERCASE>/clickhouse-prod-single:<RELEASE_TAG>` ด้วย `GITHUB_TOKEN`. Workflow **ไม่ได้ deploy** Portainer. ก่อนรัน ผู้ดูแล GitHub ต้องตั้ง environment `production-images` ให้มี required reviewers และจำกัด branch; ตั้ง environment variable `APPROVED_CLICKHOUSE_BASE_IMAGE` (ClickHouse 26.8 patch พร้อม `@sha256:`). Job ต้องมีสิทธิ์ `packages: write`; package ที่มีอยู่แล้วต้องให้ repository นี้มี Actions write access. ผู้อนุมัติตรวจ Git SHA และ base digest ก่อนอนุมัติ job; Release/Security owner ตรวจผล smoke/scan จริงหลัง job เสร็จก่อนอนุมัติให้ใช้ digest.

หาก job หยุดที่ **Validate release inputs and approved base image** ให้ผู้ดูแลเปิด repository **Settings → Environments → production-images** แล้วตรวจ **Environment variables** (ไม่ใช่กรอกในช่อง `release_tag`). Workflow ใช้ค่านี้เพียงรายการเดียว:

| ชื่อ | ตำแหน่ง | รูปแบบที่รับ |
| --- | --- | --- |
| `APPROVED_CLICKHOUSE_BASE_IMAGE` | Environment variable | Approved ClickHouse `:26.8.x.y@sha256:<64-hex>` |

ตรวจว่า environment มี required reviewers และ branch restriction เป็น default branch ก่อนรัน workflow ใหม่. `PROD_REGISTRY`, `PROD_IMAGE_NAMESPACE`, `PROD_REGISTRY_USERNAME` และ `PROD_REGISTRY_PASSWORD` ไม่จำเป็นสำหรับ workflow นี้แล้ว. GHCR tag อาจถูกเขียนทับได้; ขั้นตรวจ tag เดิมใน workflow เป็นเพียง best-effort และ deployment ต้องใช้ digest ที่ตรวจรับแล้ว. หาก package เป็น private ให้กำหนด pull access ให้ Portainer hosts ผ่านวิธีที่ Security owner อนุมัติ.

การใช้ GHCR ตามคำขอ release นี้ต่างจาก CI/CD baseline `GitHub → Jenkins → Harbor → Trivy → Portainer` ใน [AGENTS.md](../AGENTS.md). ให้ Architecture/Security/Release owner ทบทวนและอนุมัติ registry และ package access ใน change record ก่อนถือเป็น production release; workflow นี้ยังไม่ใช่การอนุมัติ security exception.

หลัง publish ให้ Release owner บันทึก **manifest digest ที่ GHCR คืนจริง** แล้วกำหนด `CLICKHOUSE_SINGLE_IMAGE=ghcr.io/<GITHUB_OWNER_LOWERCASE>/clickhouse-prod-single@sha256:<64-hex>` ในช่องทาง config ที่อนุมัติ. Tag ไม่ใช่ค่า image สำหรับ Compose production. Build/smoke/scan ของ workflow ไม่ได้พิสูจน์ S3, network, backup หรือ workload บน host จริง.

เส้นทาง B ยังไม่มี Dockerfile/pipeline ที่ทำ immutable image ครบทั้ง Keeper และ ClickHouse 1S2R. `CLICKHOUSE_PROD_IMAGE`, `KEEPER_PROD_IMAGE`, `PORTAINER_AGENT_PROD_IMAGE` ต้องมาจาก release/scan ที่อนุมัติพร้อม digest; **ห้าม**นำ image single-node ไปใช้แทน replicated build. ปิด P0-01 และ P0-08 ใน [worklist](PRODUCTION_READINESS_SPECIALIST_WORKLIST.md) ก่อนออก release.

## 5. การติดตั้ง Portainer Management Plane

Portainer Server ของ PROD ต้องอยู่ใน management zone แยกจาก data hosts. Repo นี้ **ไม่มี** production management-plane Compose หรือขั้นตอนติดตั้งที่ตรวจรับแล้ว; Platform owner ต้องจัดหา approved deployment artifact และบันทึก version/digest, TLS, SSO/MFA, RBAC, audit และ backup ของ Portainer data. จำกัด UI 9443 ให้ management VPN และ Agent 9001 ให้ Portainer Server เท่านั้น. Agent ใน multi-host Compose อยู่ใต้ profile `agent`; อย่าเปิดซ้ำกับ Agent ที่ติดตั้งแยก.

เมื่อ management plane ผ่าน review ให้สร้าง Portainer environment สำหรับ host/role ที่อนุมัติและทดสอบ connection โดยไม่เผยแพร่ service เพิ่ม. ใน **Stacks → Add stack → Git repository** ให้ใช้ repository URL, immutable Git release tag/SHA และ Compose path ที่ตรง environment. ห้ามใช้ mutable `main` เป็น deployment ref. ตรวจว่า Portainer ดึงไฟล์ใน Git ref นั้นได้จริง รวมถึง bind-mount dependencies ของเส้นทาง B; relative bind mounts ปัจจุบันยังเป็น blocker. ดู [Portainer production runbook](../runbooks/04_portainer_prod_deployment.md).

## 6. การจัดการ Secrets และ Environment Variables

ส่ง secret ผ่านกลไกที่ Security owner อนุมัติและตรวจ RBAC ของ Portainer/Docker administrators. ห้าม commit `.env` หรือแนบผล `docker compose config` แบบเต็ม เพราะคำสั่งขยายค่า secret. `.env.example` เป็นค่า DEV/UAT และ **ห้ามใช้กับ PROD**. ค่า `TBD`/placeholder ต้องหยุดก่อน deploy.

| เส้นทาง | ตัวแปรที่ต้องกำหนด |
| --- | --- |
| A: image/host | `CLICKHOUSE_SINGLE_IMAGE` (digest), `PROD_BIND_IP` (private IPv4 ที่อยู่บน host จริง) |
| A: ClickHouse | `CLICKHOUSE_ADMIN_PASSWORD`, `CLICKHOUSE_ETL_PASSWORD`, `CLICKHOUSE_BI_PASSWORD`, `CLICKHOUSE_API_PASSWORD`, `CLICKHOUSE_MONITORING_PASSWORD` |
| A: S3 cold disk | `CLICKHOUSE_S3_ENDPOINT` (HTTPS และ path ลงท้าย `/`), `CLICKHOUSE_S3_ACCESS_KEY`, `CLICKHOUSE_S3_SECRET_KEY`, `S3_REGION` |
| B: artifacts/hosts | `KEEPER_PROD_IMAGE`, `CLICKHOUSE_PROD_IMAGE`, `PORTAINER_AGENT_PROD_IMAGE` (ทุกตัวเป็น digest), `HOST_NODE1_IP`, `HOST_NODE2_IP`, `HOST_NODE3_IP` |
| B: services/S3 | `CLICKHOUSE_ADMIN_USER` และ ClickHouse/S3 credentials ที่ Compose อ้างถึง; Keeper IDs และ shard/replica กำหนดใน Compose แต่ต้องตรวจกับ topology จริง |

ก่อนเส้นทาง A รัน `python3 scripts/validate_prod_single_env.py` ใน controlled shell ที่ inject ค่าอนุมัติแล้ว; script ตรวจ **รูปแบบ** ไม่พิสูจน์ว่า registry/credentials/S3 ใช้งานได้. สำหรับเส้นทาง B ตรวจรายการตัวแปรทุกตัวจาก Compose และ config แล้วทำ positive/negative secret-injection test ใน isolated environment. Environment variables มองเห็นได้แก่ Docker/Portainer administrators ตามสิทธิ์ของระบบ.

## 7. เส้นทาง A — PROD Single Node (ไม่มี HA)

**ขอบเขต:** ชื่อ artifact เป็น `prod-single` แต่ตาม [AGENTS.md](../AGENTS.md) การรันบน host เดียวเป็น DEV/UAT. ขั้นตอนนี้ใช้เตรียม/ตรวจรับ database foundation; ไม่ใช่การเปิด production traffic หรือรับรอง HA. อ่าน [คู่มือ single-node แบบละเอียด](PROD_SINGLE_NODE_INSTALLATION_GUIDE.md) ก่อนทำบน host.

1. ปิด host/network/S3/secret preflight ในส่วน 2–6; ยืนยันว่า `CLICKHOUSE_SINGLE_IMAGE` เป็น digest จาก release ที่ scan ผ่าน. ตรวจ capacity ของ named volumes `clickhouse_single_data` และ `clickhouse_single_logs` บน Docker data root; S3 cold disk ไม่ใช่ backup.
2. ใน approved checkout และ controlled environment ที่มีค่าอนุมัติ รันคำสั่งด้านล่าง **ก่อน** ส่ง stack เข้า Portainer. ห้ามบันทึก expanded config หรือ secret ใน terminal transcript.

   ```bash
   python3 scripts/validate_prod_single_env.py
   python3 governance/policy_linter.py
   docker compose -f compose/docker-compose.prod-single.yml config --quiet
   ```

3. หลัง human approval สำหรับการทดสอบ ให้สร้าง Git-backed stack ที่ชี้ `compose/docker-compose.prod-single.yml` บน environment ที่อนุมัติ. Inject variables จากข้อ 6 ผ่านช่องทางที่อนุมัติ แล้วให้ operator ตรวจ Git SHA, digest, private bind IP, port allowlist และ persistent volumes ก่อนกด deploy.
4. ตรวจผลส่วน 9–11. SQL init 01–04 ใน image ทำงานเฉพาะการสร้าง data volume ครั้งแรก; เปลี่ยน image ไม่ใช่ migration. ห้ามลบ volume เพื่อให้ SQL init ทำซ้ำ.

**Stop condition:** preflight ล้มเหลว, ไม่มี independent backup/restore plan, S3/TLS ใช้ไม่ได้, image ไม่ใช่ digest, port เข้าถึงจาก source ที่ไม่อนุญาต หรือมีค่า `TBD` ที่กระทบ deployment ให้หยุดและส่งคืนเจ้าของ gate.

## 8. เส้นทาง B — PROD Multi-Host HA (3 Failure Domains)

เส้นทางนี้เป็น **target architecture** ตาม [คู่มือ multi-host](PROD_INSTALLATION_AND_OPERATIONS_GUIDE.md) และ [runbook](../runbooks/04_portainer_prod_deployment.md). Compose 3 ไฟล์ยังไม่ใช่ package ที่ deploy เป็น PROD ได้ตรง ๆ:

| Blocker | สิ่งที่ต้องส่งมอบ/ตรวจรับก่อน deploy |
| --- | --- |
| SQL init ใช้ local `MergeTree`/`ReplacingMergeTree` และ MV ไม่ replicated | Replicated DDL/Keeper paths, distributed DDL, migration/backfill, syntax/runtime tests, `system.replicas` และ data parity บน 2 nodes |
| Node 01/02 Compose รวม Keeper กับ ClickHouse | Approved Git-backed Keeper-only และ ClickHouse-only stages หรือ controlled profiles; bootstrap quorum ก่อนเปิด ClickHouse traffic |
| Relative bind mounts ของ config/SQL | Immutable config artifact หรือ approved absolute paths ที่ทดสอบกับ Portainer Git stack จริง |
| Pipeline/observability/data path/DR ยังไม่ครบ | Approved digests/scan, production ingestion/dbt/API, monitoring/alerts/log shipper, isolated restore drill และ host-loss/rejoin evidence |

เมื่อทุก blocker ปิดและ CAB อนุมัติแล้ว ลำดับคือ management plane → Keeper 03 บน Node 03 → Keeper 01 บน Node 01 → Keeper 02 บน Node 02 → quorum gate → ClickHouse replica 01 → replica 02 → replication/data parity → monitoring/backup/restore → canary traffic. แต่ละ stage ต้องใช้ Git-backed release และมี checkpoint/rollback ใน change record. ห้ามนำ full node stack ปัจจุบันไป bootstrap Keeper ทีละตัวใน Portainer editor. `system.replicas` ว่างถือว่า **replication gate ไม่ผ่าน** แม้ `/ping` ผ่าน. ก่อน gate ครบ หยุดที่การออกแบบและทดสอบใน isolated environment.

## 9. การตรวจรับหลังติดตั้ง

ให้ operator เก็บผลจริงพร้อมเวลา, host, Git SHA, image digest และ exit code แบบ redacted; อย่ารายงานว่า “ผ่าน” จากตัวอย่างคำสั่ง. หลัง deploy ที่ได้รับอนุมัติ ตรวจ read-only บน host:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
ss -lnt
docker compose -f compose/docker-compose.prod-single.yml ps
```

คำสั่ง `docker compose ... ps` ใช้กับเส้นทาง A และต้องมี context/env เดียวกับ stack; สำหรับเส้นทาง B ใช้ Compose file ของ node นั้น. ตรวจ image digest จริงด้วย registry/Portainer, health status, bind IP และ network positive/negative tests. ใช้ client ที่ผ่าน approved secret method รัน read-only SQL:

```sql
SELECT version(), currentUser();
SELECT name, engine FROM system.databases WHERE name IN ('raw','core','mart','serving');
SELECT database, name, engine FROM system.tables WHERE database IN ('raw','core','mart','serving') ORDER BY database, name;
SELECT name, path, free_space, total_space FROM system.disks;
```

เส้นทาง B เพิ่ม `system.clusters`, `system.replicas`, `system.replication_queue`, Keeper quorum, identical table inventory/checksums และ host-loss/rejoin test ตาม [คู่มือ multi-host](PROD_INSTALLATION_AND_OPERATIONS_GUIDE.md). `/ping` พิสูจน์เพียง process ตอบ ไม่พิสูจน์ auth, S3, replication หรือ data correctness. ตรวจ least privilege ด้วยบัญชี service จริง รวมถึงการปฏิเสธ query ที่ไม่ได้สิทธิ์ และทำ source-to-serving reconciliation ด้วยข้อมูลที่ Data Owner อนุมัติ.

## 10. Backup, Restore และ DR

Backup ต้องเขียนไป S3-compatible storage ที่ **แยกจาก ClickHouse host/cold disk** และมี retention/credential/KMS ที่อนุมัติ. ระบุฐาน/metadata ทั้งหมดใน recovery scope, schedule, alert เมื่อ backup ล้มเหลวหรือเก่าเกินเกณฑ์, และ owner. RPO ≤ 1 ชั่วโมง/RTO ≤ 4 ชั่วโมงเป็นเพียง target ที่ต้องได้ business sign-off; ค่ารับจริงยัง `TBD`.

ก่อนเปิด production traffic ต้องทำ **non-destructive restore drill** ไป isolated namespace/host, ตรวจ inventory, row counts, aggregates, hashes/query results และบันทึกเวลาจริงเพื่อเทียบ RPO/RTO. [backup runbook](../runbooks/02_backup_and_restore_operations.md) เป็นแนวทาง; [สคริปต์ backup](../scripts/backup_clickhouse.sh) ปัจจุบันครอบคลุมแค่ `mart` และ [สคริปต์ restore](../scripts/restore_test.sh) ตรวจเพียง count พร้อม cleanup ชื่อคงที่ จึง **ยังใช้เป็น production DR automation ไม่ได้**. ดู P0-07 ใน [worklist](PRODUCTION_READINESS_SPECIALIST_WORKLIST.md). ห้ามทดลอง restore ทับ production data.

## 11. Monitoring และ Observability

ใช้ Prometheus/Grafana/Loki ใน management zone ที่ผ่าน review พร้อม collector/log shipper และ alert routing. Repo มี [Prometheus UAT config](../monitoring/prometheus/prometheus.uat.yml), [rules](../monitoring/prometheus/alert_rules.yml), [Grafana dashboard](../monitoring/grafana/dashboards/clickhouse_overview.json) และ [Loki config](../monitoring/loki/loki-config.yml) แต่ยังไม่มี production management stack หรือหลักฐาน scrape/alert/log delivery. ห้ามใช้ UAT targets เป็น PROD โดยเปลี่ยนชื่ออย่างเดียว.

อย่างน้อยต้องแสดง target `9363` ของ ClickHouse, Keeper metrics/health ตาม config ที่อนุมัติ, disk/parts/merges, replication lag/queue, S3 errors, ingestion/dbt freshness, API error/latency, backup age และ Portainer/host health. ทดสอบ alert firing → notification → on-call acknowledgement และค้น log ที่ redacted ได้จริง. Thresholds, retention และ on-call routing ยัง `TBD` จน SRE/Data Owner อนุมัติ.

## 12. Day-2 Operations

| ความถี่/เหตุการณ์ | ผู้รับผิดชอบ | ตรวจและบันทึก |
| --- | --- | --- |
| ทุกวัน | SRE | Host/containers, disk headroom, S3 errors, backup age, alert delivery; สำหรับ B เพิ่ม Keeper quorum และ replica queue/lag |
| ทุก batch | Data Engineer/Data Owner | Source counts/hash, `_batch_id`, freshness, dbt test, reconciliation และ quarantine/replay |
| ทุก release | Release/CAB | Git SHA + digest, scan/SBOM, Compose/SQL diff, canary, rollback compatibility และ change window |
| Incident | On-call + domain owner | Severity, timeline, blast radius, logs/metrics แบบ redacted, [troubleshooting runbook](../runbooks/03_troubleshooting_and_failover.md), recovery evidence |
| ตามรอบ DR ที่อนุมัติ | Backup/SRE + Business | Isolated restore drill และ RPO/RTO ที่วัดจริง |

ห้ามแก้ Git stack ใน Portainer editor, ลบ volume, rotate credential หรือแก้ firewall เพื่อแก้เหตุเฉพาะหน้าโดยไม่มี change/incident approval ที่เกี่ยวข้อง.

## 13. Rollback Procedures

เตรียม rollback **ก่อน** deploy: เก็บ Git SHA, Compose/config/SQL version, image digest เดิม, schema/data compatibility, backup/restore point, owner และ stop criteria. เมื่อ canary/health/data check ไม่ผ่าน ให้หยุด traffic หรือกลับไป release ที่อนุมัติผ่าน Git-backed stack ตาม change plan; ตรวจ health, data parity และ alert อีกครั้ง. การย้อน image ไม่ย้อน SQL schema หรือ data ที่เขียนแล้ว. หากมี migration/DDL หรือ data loss risk ให้ DBA/Data Owner อนุมัติ recovery plan แยก. **ห้าม**ใช้ `docker compose down -v`, ลบ database/volume หรือ restore ทับ production เพื่อ rollback แบบเร่งด่วน.

## 14. Production Readiness Gate Checklist

ทำเครื่องหมายเฉพาะเมื่อแนบหลักฐานจริงและมีผู้ตรวจทานแยกจากผู้จัดทำ; ช่องว่างหมายถึงยังไม่ผ่าน.

- [ ] Host/NTP/capacity/Docker, DNS/private IP และ firewall positive/negative tests ผ่านบนทุก failure domain
- [ ] Git SHA, image patch/digest, GHCR package permissions, tag uniqueness check, SBOM/Trivy scan และ TLS/CA/secret delivery ผ่าน review
- [ ] Compose/XML/SQL parser และ policy checks ผ่านด้วย approved release/config; ไม่มี relative bind-mount blocker
- [ ] 3 Keeper members มี quorum และ 2 ClickHouse replicas ใช้ replicated tables จริง; parity และ host-loss/rejoin ผ่าน
- [ ] Source → S3/Parquet → raw → core → mart → serving, dbt tests, API RBAC และ reconciliation ผ่านด้วย approved workload
- [ ] Metrics/alerts/log delivery, independent backup และ isolated restore drill ผ่าน; RPO/RTO มีผลวัดและ business sign-off
- [ ] Architecture, DBA/Data Owner, Security, Network, Platform/SRE, Business และ Release/CAB รับ residual risks และอนุมัติ production promotion

**สถานะปัจจุบัน: ไม่ผ่าน production readiness gate.** โดยเฉพาะ P0-01 ถึง P0-08 ใน [worklist](PRODUCTION_READINESS_SPECIALIST_WORKLIST.md) ยังต้องมีหลักฐานปิดงาน. เส้นทาง A ไม่สามารถผ่านข้อ 3 failure domains ตามนโยบายปัจจุบัน.

## 15. Handoff Contract

ทุก change/release ต้องส่งรายงาน 6 หัวข้อต่อไปนี้ พร้อมลิงก์หลักฐานและผลคำสั่งจริง:

| หัวข้อ | สิ่งที่ต้องรายงาน |
| --- | --- |
| Scope & Sources Inspected | Git SHA, Compose/Dockerfile/SQL/config/runbook ที่ตรวจ, topology และ environment |
| Assumptions & Decisions | ค่า `TBD`, approved IP/DNS/CIDR, image digest, S3, sizing, RPO/RTO และผู้ตัดสินใจ |
| Security & Operational Impact | Port binds, RBAC/secrets, storage/volumes, compatibility, downtime, rollback limits |
| Validation Commands & Results | คำสั่ง, exit code, output แบบ redacted, วันที่/host, reviewer; แยก syntax/smoke จาก runtime/DR |
| Remaining TBDs & Residual Risks | P0/P1 ที่ยังไม่ปิด, failure scenarios และ owner/date ของการแก้ |
| Human Approval Required | ผู้อนุมัติ production promotion, destructive migration/restore, firewall/credential changes และ security exceptions |

การแก้เอกสารรอบนี้ไม่มีผลต่อ Compose, SQL, volume หรือ live deployment. การใช้งานจริงยังขึ้นกับการปิด gate และ human sign-off ข้างต้น.
