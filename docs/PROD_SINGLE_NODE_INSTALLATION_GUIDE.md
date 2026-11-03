# คู่มือติดตั้ง Production ระยะที่ 1: ClickHouse 1 Node

**สถานะ: เห็น Ubuntu 24.04.1 ถึง console login แล้ว; ยังไม่มีผล host preflight หรือ live deployment ของ stack**  
**Topology:** ClickHouse 1 instance บน Ubuntu 24 LTS, external S3-compatible storage, Git-backed Portainer stack. ไม่มี Keeper, replication, HA หรือ automatic failover. เมื่อจะขยายเป็น 3 failure domains ให้ใช้ [คู่มือ multi-host](PROD_INSTALLATION_AND_OPERATIONS_GUIDE.md) และ migration plan ที่ผ่าน review; ห้ามนำ image/stack ชุด single-node ไปเปลี่ยนชื่อเป็น HA.

## 1. สิ่งที่มีในชุดนี้

| Artifact | หน้าที่ |
| --- | --- |
| [Dockerfile.prod-single](../clickhouse/Dockerfile.prod-single) | สร้าง immutable image โดยรวม config และ local SQL 01–04; ไม่มี Keeper/1S2R config, ไม่มี Kafka demo init |
| [docker-compose.prod-single.yml](../compose/docker-compose.prod-single.yml) | ClickHouse หนึ่ง service, persistent named volumes, private-IP published ports, required env ทุกตัว |
| [validate_prod_single_env.py](../scripts/validate_prod_single_env.py) | ตรวจรูปแบบ env, private IP, image digest, HTTPS S3 และ placeholder โดยไม่พิมพ์ค่าความลับ |

ชุดนี้ทำให้ **database foundation** รันแบบโหนดเดียวได้หลังผ่าน gate. Production ingestion/CDC, dbt runtime, serving API, observability, independent backup/restore และ business acceptance ยังคงต้องทำและทดสอบก่อนเรียกว่า *Enterprise Data Lakehouse Platform พร้อมใช้งานจริงครบระบบ*. ไฟล์ UAT ไม่ถูกใช้เป็น source deployment ของ PROD.

**Impact/rollback:** เป็นไฟล์ Compose/Dockerfile ใหม่ ไม่เปลี่ยน DEV/UAT หรือ PROD 3-node stacks. SQL init 01–04 ถูกคัดลอกลง image แต่ทำงานเฉพาะการสร้าง data volume ครั้งแรกตาม entrypoint; การอัปเดต image ไม่ใช่ migration framework. Rollback ต้องใช้ Git SHA/image digest เดิมและตรวจ schema/data compatibility ก่อน redeploy; named volumes ถูกเก็บไว้ ไม่ใช้ `down -v` หรือการลบข้อมูล. ความจุของ data/log volumes อยู่บน Docker host และต้องประเมินก่อนรับข้อมูล.

## 2. สถานะ Node 01 จากหลักฐานที่ได้รับ

ภาพใน `docs/HOST_NODE1_IP/` แสดงหน้าจอ **ระหว่างติดตั้ง Ubuntu**: hostname `kpi-datalakehouse-prod01`, candidate network แบบ manual และดิสก์ `/dev/sda` ขนาดราว 1 TB ที่เสนอให้ใช้ LVM/root volume. ภาพ console ล่าสุดที่ผู้ใช้ส่งแสดง **Ubuntu 24.04.1 LTS ถึงหน้า `tty1` login** ของ hostname เดียวกันแล้ว และ cloud-init แสดง `modules:final` พร้อมข้อความว่าไม่พบ authorized SSH keys สำหรับผู้ใช้ `kpiadmin`. นี่เป็นหลักฐานว่าเครื่อง boot ถึง login prompt; **ยังไม่ยืนยัน** ว่า login สำเร็จ, cloud-init จบสมบูรณ์, SSH ใช้งานได้, IP/DNS/gateway ผ่าน, มี CPU/RAM เท่าใด, disk layout ถูกอนุมัติ หรือมี backup/storage แยก. ไม่บันทึก SSH host-key fingerprints จากหน้าจอลงคู่มือ; ให้ตรวจเทียบกับ host จริงก่อน SSH ครั้งแรก.

### ขั้นแรกหลัง login ที่ console (อ่านสถานะก่อนเปลี่ยนระบบ)

ให้ผู้ดูแล login ที่ console ด้วยบัญชีที่ได้รับอนุมัติ แล้วเก็บผลคำสั่งต่อไปนี้ใน change record โดยปกปิดข้อมูลที่ sensitive:

```bash
whoami
id
sudo -v
hostnamectl
sudo cloud-init status --long
ip -br addr
ip route
resolvectl status
timedatectl status
lsblk -f
df -h
free -h
nproc
systemctl status ssh --no-pager
```

หาก cloud-init ยังทำงาน ให้รอและตรวจ `sudo cloud-init status --wait` ก่อนติดตั้ง package หรือแก้ network. หาก login/sudo ไม่ผ่าน, interface ไม่มี approved IP, default route/DNS ผิด, เวลาไม่ synchronized หรือ filesystem ไม่ตรงแผน ให้หยุดและให้เจ้าของระบบแก้จาก console/change record ก่อน. ค่า `PROD_BIND_IP`, DNS, sizing และ mount layout จึงยัง **TBD** จนผลจริงได้รับอนุมัติ.

ข้อความ **“no authorized SSH keys”** บอกว่า SSH key สำหรับ `kpiadmin` ยังไม่ได้ provision ผ่าน cloud-init ณ เวลาที่แสดง ไม่ได้พิสูจน์ว่า SSH server ปิดหรือเปิด password login. ให้ Platform/Security owner ติดตั้ง public key ผ่าน approved identity/host-management workflow, ตรวจ fingerprint ของ SSH host key ผ่าน console, ทดสอบ key login จาก management VPN และยืนยันสิทธิ์ sudo ก่อนปรับ authentication policy. อย่าปิด password login หรือ root access แบบคาดเดาจนมีช่องทางเข้าถึงที่ทดสอบแล้ว.

หาก LVM/root ใช้พื้นที่เกือบทั้งหมด Docker named volumes จะอยู่บน filesystem ของ Docker (`docker info` ระบุ `Docker Root Dir`) ตามค่า host; ต้องยืนยัน capacity/headroom, IOPS, snapshot/restore strategy และ alert สำหรับ root filesystem ก่อนรับข้อมูลจริง. อย่าแก้ partition/LVM หรือ format disk ผ่านขั้นตอนอัตโนมัติในคู่มือนี้.

## 3. ข้อกำหนด host และเครือข่าย

1. Ubuntu 24 LTS ที่ hardened, NTP sync, DNS/route/firewall ตาม baseline องค์กร; CPU/RAM/usable storage กำหนดจาก workload และ [capacity worklist](PRODUCTION_READINESS_SPECIALIST_WORKLIST.md), ไม่อนุมานจากภาพดิสก์.
2. ติดตั้ง Docker Engine และ Compose V2 จาก repository ที่องค์กรอนุมัติ ตาม [Docker Ubuntu guide](https://docs.docker.com/engine/install/ubuntu/). ตรวจ `docker version`, `docker compose version`, `systemctl status docker`; ผู้มีสิทธิ์ `docker` เทียบเท่า root จึงต้องจำกัดกลุ่มผู้ใช้.
3. สร้าง/อนุมัติ enterprise S3 bucket และ prefix สำหรับ ClickHouse cold disk; endpoint ต้องเป็น HTTPS, มี TLS CA ที่ host/container เชื่อถือ, network egress และ lifecycle/retention ที่อนุมัติ. Backup ต้องไป independent object storage ที่ตรวจ restore ได้; S3 cold disk **ไม่ใช่ backup**.
4. Portainer Server อยู่ใน management zone ที่อนุมัติ และ agent บน host นี้ถูกติดตั้งผ่านขั้นตอน platform bootstrap ที่อนุมัติ (Portainer Server → Agent `9001/TCP` private). Stack ของ ClickHouse ต้องสร้างจาก Git ref/tag ที่อนุมัติ ไม่ใช่การแก้ Compose ใน Portainer editor. ดู [Portainer Git stack](https://docs.portainer.io/user/docker/stacks/add).

| Published port ของ single-node stack | Bind | ผู้ใช้ที่อนุมัติ | หน้าที่ |
| --- | --- | --- | --- |
| `8123/TCP` | `${PROD_BIND_IP}:8123` | API/ingestion/trusted proxy เท่านั้น | ClickHouse HTTP; production TLS termination/policy ต้องผ่าน review |
| `9000/TCP` | `${PROD_BIND_IP}:9000` | trusted BI/ETL/admin เท่านั้น | native protocol; TLS/ACL design ต้องผ่าน review |
| `9363/TCP` | `${PROD_BIND_IP}:9363` | Prometheus เท่านั้น | metrics; ไม่มี monitoring stack ใน Compose นี้ |
| `443/TCP` outbound | N/A | enterprise S3 | cold storage/backup endpoint |
| `9001/TCP` | นอก stack นี้ | Portainer Server | Agent bootstrap ที่ Platform owner ดูแล |

ไม่มี `9181`, `9234` หรือ `9009` ใน single-node stack. การ bind private IP ไม่แทน firewall allowlist; Docker published ports อาจเข้าถึงได้จาก network ที่ route ถึง host IP จึงต้องทดสอบ positive/negative source paths จริงตาม [Docker port-publishing guide](https://docs.docker.com/engine/network/port-publishing/). ห้าม expose `8123/9000/9363/9001` สู่ Internet.

## 4. Release image และค่า environment

ไฟล์ [publish-prod-images.yml](../.github/workflows/publish-prod-images.yml) เป็น workflow สำหรับ build, smoke-test, Trivy scan และ push `ghcr.io/<GITHUB_OWNER_LOWERCASE>/clickhouse-prod-single:<RELEASE_TAG>` ด้วย `GITHUB_TOKEN` โดยสั่ง `workflow_dispatch` จาก default branch พร้อม `release_tag` รูปแบบ `prod-v<major>.<minor>.<patch>` เท่านั้น. ก่อนใช้งาน ให้ GitHub administrator ตั้ง environment ชื่อ `production-images` พร้อม **required reviewers** และจำกัด deployment branch เป็น default branch; ตั้ง environment variable `APPROVED_CLICKHOUSE_BASE_IMAGE` (ClickHouse 26.8 patch พร้อม digest). Workflow ใช้ `packages: write`; package ที่มีอยู่แล้วต้องให้ repository นี้มี Actions write access. ผู้อนุมัติตรวจ Git SHA และ base-image digest ก่อนอนุมัติ job; Release/Security owner ตรวจผล smoke/scan จริงหลัง job เสร็จก่อนอนุมัติให้ใช้ digest. GHCR tag check เป็น best-effort; ให้ deploy ด้วย manifest digest ที่ตรวจรับแล้ว. หาก package เป็น private ต้องจัด pull access ให้ Portainer hosts ผ่านวิธีที่อนุมัติ. Workflow นี้เผยแพร่ image เท่านั้น; การนำ digest ไปใช้ใน Portainer ยังต้องผ่าน production readiness gate และ approval แยกต่างหาก.

Pipeline ที่อนุมัติ build Dockerfile จาก repository root และ push ไป registry ที่มี scan/SBOM/review. `CLICKHOUSE_BASE_IMAGE` ต้องเป็น approved ClickHouse 26.8 **patch+digest**; tag เพียงอย่างเดียวใช้ไม่ได้. ตัวอย่างคำสั่งเชิงรูปแบบ (ไม่ใส่ secret):

```bash
docker build \
  --build-arg CLICKHOUSE_BASE_IMAGE='<APPROVED_CLICKHOUSE_26_8_PATCH@sha256:DIGEST>' \
  -f clickhouse/Dockerfile.prod-single \
  -t 'ghcr.io/<GITHUB_OWNER_LOWERCASE>/clickhouse-prod-single:<RELEASE>' .
docker push 'ghcr.io/<GITHUB_OWNER_LOWERCASE>/clickhouse-prod-single:<RELEASE>'
```

หลัง push ให้ resolve digest ที่ GHCR และตั้ง `CLICKHOUSE_SINGLE_IMAGE=ghcr.io/<GITHUB_OWNER_LOWERCASE>/clickhouse-prod-single@sha256:<64 hex>`. อย่านำ placeholder ในตัวอย่างไป build/pull จริง. `Dockerfile.prod-single` ใช้ local DDL เดิม; การใช้ `MergeTree` แบบไม่มี replication **ถูกต้องตามขอบเขต 1 Node** แต่ไม่รองรับ HA.

| Env ที่ Portainer/secret manager ต้องส่ง | ค่า/ขอบเขต |
| --- | --- |
| `CLICKHOUSE_SINGLE_IMAGE` | approved immutable image digest |
| `PROD_BIND_IP` | private IPv4 ของ host ที่ตรวจจริงและ Network owner อนุมัติ |
| `CLICKHOUSE_ADMIN_PASSWORD`, `CLICKHOUSE_ETL_PASSWORD`, `CLICKHOUSE_BI_PASSWORD`, `CLICKHOUSE_API_PASSWORD`, `CLICKHOUSE_MONITORING_PASSWORD` | strong unique credentials จาก approved secret management; ห้าม commit หรือใช้ `.env.example` ของ UAT |
| `CLICKHOUSE_S3_ENDPOINT` | `https://<approved-object-store>/<bucket>/<prefix>/` ลงท้าย `/`; prefix ของ cold disk แยกจาก backup |
| `CLICKHOUSE_S3_ACCESS_KEY`, `CLICKHOUSE_S3_SECRET_KEY`, `S3_REGION` | สิทธิ์ขั้นต่ำที่ storage owner อนุมัติ; ห้ามพิมพ์ใน log |

`validate_prod_single_env.py` ตรวจรูปแบบเท่านั้น ไม่พิสูจน์ว่า IP อยู่บน host, image digest มีอยู่, credentials ใช้ได้ หรือ S3 เป็น independent storage. ค่า secret ที่ inject เป็น environment จะมองเห็นได้แก่ Docker/Portainer administrators ตามสิทธิ์ของระบบ; Security owner ต้องอนุมัติวิธีส่ง secret และ audit. อย่าบันทึกผล `docker compose config` แบบเต็มเพราะขยายค่า secret.

## 5. Preflight ก่อน deploy

Platform owner ทำบน approved release checkout/validation workspace; ใช้ค่า environment จาก approved secret mechanism และเก็บ output แบบ redacted:

```bash
python3 scripts/validate_prod_single_env.py
docker compose -f compose/docker-compose.prod-single.yml config --quiet
python3 governance/policy_linter.py
```

ตรวจเชิงระบบเพิ่มเติม:

```bash
hostnamectl
ip -br addr
ip route
timedatectl status
docker version
docker compose version
docker info --format '{{.DockerRootDir}}'
df -h
lsblk -f
```

ให้ Network/Security owner ตรวจ `PROD_BIND_IP` เป็น interface ของเครื่อง, allowlist inbound ตามตาราง, S3 HTTPS egress, DNS/TLS CA และ registry access. ให้ Storage owner ตรวจ S3 bucket/prefix/permissions/lifecycle และแผน restore. ให้ DBA ตรวจ image digest, config, SQL init และ capacity. **หยุด** หาก preflight fail, มี `TBD`, host disk ไม่พอ, ไม่มี backup destination หรือยังไม่อนุมัติ security boundary.

## 6. ติดตั้งจาก Portainer Git Stack

ขั้นตอนนี้ให้มนุษย์ผู้มีสิทธิ์ Release/Platform ทำหลังผ่าน gate และมี change approval:

1. ติดตั้ง/ตรวจ Portainer Agent ของ host ตาม [Portainer Agent documentation](https://docs.portainer.io/admin/environments/add/docker/agent), ผูก environment ชื่อที่อนุมัติ เช่น `prod-single-node01`, ตรวจ RBAC, management VPN และ 9001 allowlist.
2. ใน environment นี้เลือก **Stacks → Add stack → Git repository**; ระบุ approved repository URL และ immutable release tag/SHA, Compose path `compose/docker-compose.prod-single.yml`.
3. ตั้ง environment variables ข้างต้นผ่าน approved secret mechanism/Portainer integration; ตรวจว่า `CLICKHOUSE_SINGLE_IMAGE` เป็น digest ที่ scan ผ่านและ `PROD_BIND_IP` เป็น private IP จริง. อย่าใช้ `.env.example`, UAT image หรือ mutable branch.
4. ตรวจ preview/config ของ stack โดยไม่เปิดเผย secret; deploy หลัง reviewer ลงนาม. Stack นี้มีเพียง ClickHouse service; named volumes สร้างบน Docker host. อย่าเปิด GitOps auto-update ก่อนมี release/rollback policy.
5. ตรวจ container status, logs ที่ redacted, volumes, published ports และ health. ถ้า init ล้มเหลวให้หยุดและเก็บ log; อย่าลบ volume หรือใช้ `CLICKHOUSE_ALWAYS_RUN_INITDB_SCRIPTS` เพื่อกลบปัญหา.

## 7. ตรวจรับหลังติดตั้งบน host จริง

ใช้ approved admin client ที่ไม่ใส่ password ใน shell history/process arguments. บันทึกคำสั่ง/ผลแบบไม่เผย secret:

```sql
SELECT version();
SELECT name, engine FROM system.databases WHERE name IN ('raw','core','mart','serving') ORDER BY name;
SELECT database, name, engine FROM system.tables WHERE database IN ('raw','core','mart','serving') ORDER BY database, name;
SELECT name, path, free_space, total_space FROM system.disks;
SELECT name, volume_name, volume_priority, disks FROM system.storage_policies;
```

จาก trusted client ทดสอบ HTTP `/ping` และ native login ตาม role, query read/write ตามสิทธิ์, negative access ไปฐานที่ไม่อนุญาต, S3 cold disk write/read/TTL movement ด้วย fixture ที่อนุมัติ. `/ping` และ container health ตรวจ process เท่านั้น. ตรวจ `docker ps --format`, `ss -lnt`, firewall positive/negative access และ alert disk/resource. ทดสอบ restart แบบควบคุมว่าข้อมูลและ role ยังอยู่; อย่าทดสอบด้วยการลบ volume.

ก่อนรับ **ข้อมูลจริง** ต้องมี ingestion/source contract, approved quality/reconciliation, dbt transformation, governed serving/API, monitoring/alerting และ **independent backup + non-destructive restore drill** ที่ตรวจ schema/count/hash/revenue และวัด RPO/RTO ที่ business owner ลงนาม. [Production worklist](PRODUCTION_READINESS_SPECIALIST_WORKLIST.md) ระบุ P0 ที่ยังไม่ปิด. `scripts/backup_clickhouse.sh` และ `scripts/restore_test.sh` ปัจจุบันไม่ใช่ production backup gate เพราะครอบคลุมไม่ครบและตรวจผลไม่เพียงพอ.

## 8. ปฏิบัติการและการขยายในอนาคต

| งาน | ความถี่/หลักฐานที่ต้องกำหนด |
| --- | --- |
| Health/disk/parts/query errors | Dashboard/alert ที่ทดสอบจริง, owner/on-call `TBD` |
| Data quality/freshness | source→raw→core→mart→serving reconciliation ที่ fail closed, threshold `TBD` |
| Backup/restore | independent S3, inventory/checksum, scheduled isolated drill, RPO/RTO signed `TBD` |
| Change/rollback | approved Git SHA/image digest, config/SQL diff, impact, maintenance window, no volume deletion |
| Capacity | ingest/query benchmark, disk/merge/cache growth, S3 request and egress cost |

การเพิ่ม Node 02/03 ในภายหลังเป็น **migration** จาก local MergeTree ไป replicated tables พร้อม Keeper quorum, backfill และความเสี่ยง downtime; ไม่มี automatic conversion เพียงเพิ่ม container. ต้องออกแบบและทดสอบแยกตาม [multi-host guide](PROD_INSTALLATION_AND_OPERATIONS_GUIDE.md).

## Handoff Contract

- **Scope & Sources Inspected:** UAT/prod Compose, Dockerfile, ClickHouse config/SQL, backup scripts, AGENTS.md, ภาพ installer ใน `docs/HOST_NODE1_IP/` และภาพ console login ล่าสุดจากผู้ใช้
- **Assumptions & Decisions:** เริ่ม ClickHouse foundation 1 Node โดยใช้ external S3 และ Git-backed Portainer; ไม่มี HA; org IP/sizing/secrets/backup policy ยัง `TBD`
- **Security & Operational Impact:** เปิดเฉพาะ private-IP ports 8123/9000/9363 ตาม allowlist; image immutable และ secret injection ต้องผ่าน security review; named volumes อยู่บน host เดียวและต้อง backup อิสระ
- **Validation Commands & Results:** `docker compose config --quiet` ผ่านด้วยค่า dummy ที่ใช้ตรวจ syntax; เมื่อไม่กำหนด image/IP คำสั่ง fail ตามที่ตั้งใจ. JSON config มี service `clickhouse` เพียงตัวเดียวและ publish 8123/9000/9363 บน IP ที่กำหนด. Preflight ผ่าน valid-format fixture และปฏิเสธ endpoint/placeholder ที่ไม่ปลอดภัย; Dockerfile `COPY` source ครบ 9 รายการ, `py_compile` ผ่าน, XML parser ผ่าน 8 ไฟล์, policy linter ผ่าน 9 กฎ, relative links 257 รายการไม่มีปลายทางหาย และ `git diff --check` ผ่าน. Docker daemon ใน workspace ไม่ทำงาน จึงยัง build image, รัน SQL/init หรือทดสอบ host จริงไม่ได้
- **Remaining TBDs & Residual Risks:** host/IP/storage confirmation, approved image/S3/TLS/secret mechanism, actual pipeline/monitoring/backup/restore, business RPO/RTO และ capacity evidence
- **Human Approval Required:** Platform/Network/Security/DBA/Data Owner/Business/Release owner ก่อน production deploy และรับข้อมูลจริง
