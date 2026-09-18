# Runbook 04: Production Multi-Host Deployment ด้วย Portainer

เอกสารนี้สำหรับ **Production เท่านั้น** สำหรับ UAT Single Node ให้ใช้
[Runbook 01: UAT Deployment](01_portainer_git_stack_deployment.md)
ดู target architecture ที่ [Production Architecture Design](../docs/architecture/PROD_ARCHITECTURE.md)

## 1. สถานะและข้อห้าม

> [!CAUTION]
> ห้าม deploy Production จาก Compose ปัจจุบันจนกว่า Production Readiness Gate
> ในหัวข้อ 4 จะผ่านครบและได้รับ human approval เป็นลายลักษณ์อักษร

Production baseline คือ ClickHouse 1 shard x 2 replicas และ ClickHouse Keeper
3 members บน failure domains แยกกันอย่างน้อย 3 แห่ง การรันทั้งหมดบน host เดียว
ไม่ถือเป็น High Availability

เอกสารนี้ไม่อนุญาตให้ AI agent หรือ automation:

- Promote ขึ้น Production โดยไม่มี human approval
- เปลี่ยน production firewall โดยอัตโนมัติ
- ลบ database, Docker volume หรือ backup
- Rotate credentials โดยไม่มี change record
- ยกเว้น vulnerability หรือ compliance finding ให้ตนเอง

## 2. Production Topology

| Failure domain | Portainer environment | Compose path | Services |
|---|---|---|---|
| Host 01 | `prod-node1` | `compose/docker-compose.prod-node1.yml` | Keeper 01, ClickHouse Replica 01 |
| Host 02 | `prod-node2` | `compose/docker-compose.prod-node2.yml` | Keeper 02, ClickHouse Replica 02 |
| Host 03 | `prod-keeper3` | `compose/docker-compose.prod-keeper3.yml` | Keeper 03 tie-breaker |
| Management | `prod-management` | `TBD` | Portainer Server, Prometheus, Grafana, Loki |
| Enterprise S3 | External managed service | `TBD` | Lake storage and independent backup target |

Portainer Server ต้องติดตั้งบน management host แยกจาก ClickHouse failure domains
และเชื่อมต่อ Node 1-3 ผ่าน Portainer Agent หรือ approved Edge Agent configuration

## 3. Network and Port Matrix

| Port | Source | Destination | Purpose |
|---:|---|---|---|
| `9001/TCP` | Portainer Server | Portainer Agents | Agent management |
| `9181/TCP` | ClickHouse nodes | Keeper 01-03 | Keeper client |
| `9234/TCP` | Keeper 01-03 | Keeper 01-03 | Raft peer traffic |
| `9009/TCP` | ClickHouse 01-02 | ClickHouse 01-02 | Interserver replication |
| `9000/TCP` | Trusted BI/ETL | ClickHouse 01-02 or internal LB | Native protocol |
| `8123/TCP` | Trusted API/BI | ClickHouse 01-02 or TLS proxy | HTTP API |
| `9363/TCP` | Prometheus | ClickHouse 01-02 | Metrics |
| `9443/TCP` | Management VPN | Portainer Server | Admin UI |
| `443/TCP` | ClickHouse nodes | Enterprise S3 endpoint | Lake and backup storage |

Keeper `9181/9234`, ClickHouse `9009`, Portainer Agent `9001` และ metrics `9363`
ห้ามเปิดสู่ Internet ต้องจำกัดด้วย firewall/security groups ไปยัง source CIDR ที่
อนุมัติเท่านั้น ค่า IP, DNS, load balancer และ CIDR จริงให้ระบุเป็น `TBD` จนกว่า
Network/Security owner จะอนุมัติ

## 4. Production Readiness Gate

ทุกข้อด้านล่างต้องมีหลักฐานก่อน deploy:

- [ ] Host 01-03 อยู่คนละ failure domain จริง
- [ ] Ubuntu 24 LTS hardened และ NTP synchronized
- [ ] Static IP/DNS ของทุก node ได้รับอนุมัติ
- [ ] East-west firewall matrix ผ่านการทดสอบ
- [ ] ClickHouse image pin เป็น 26.8 LTS patch และ digest ที่อนุมัติ
- [ ] Portainer image/agent pin เป็น version/digest ที่อนุมัติ
- [ ] Trivy scan ผ่าน policy หรือมี security exception จากมนุษย์
- [ ] Enterprise S3 endpoint, bucket, KMS และ lifecycle ได้รับอนุมัติ
- [ ] Secrets อยู่ใน approved secret manager/Portainer secret mechanism
- [ ] Keeper config ผ่าน parser และ cross-host connectivity test
- [ ] ClickHouse cluster config ผ่าน parser และ replica DNS resolution test
- [ ] Resource sizing ผ่าน capacity/load test
- [ ] Monitoring/alerting สำหรับ multi-host PROD ถูกจัดทำแยกจาก UAT config
- [ ] Backup ไป independent S3 สำเร็จ
- [ ] Non-destructive restore drill สำเร็จและวัด RPO/RTO จริง
- [ ] Rollback/change record ได้รับ CAB/Change Manager approval
- [ ] Platform, DBA, Security, Network และ Data Owner sign-off

### Blocking gaps ใน repository ปัจจุบัน

รายการต่อไปนี้ยังต้องแก้ก่อน Production:

1. ClickHouse/Keeper images ใช้ tag `26.8`/`26.8-alpine` แต่ยังไม่ได้ pin patch/digest
2. Production S3 endpoint, bucket, KMS และ backup credentials ยังไม่ได้กำหนด
3. Production observability topology/configuration ยังไม่มี; ไฟล์ observability ปัจจุบัน
   ใช้ shared Docker network สำหรับ UAT Single Node
4. Compose ของ Production ยังมี relative bind mounts สำหรับ ClickHouse/Keeper ซึ่งไม่ควร
   deploy ผ่าน Portainer Git Stack จนกว่าจะเปลี่ยนเป็น immutable image หรือ absolute host path
   ที่ provision และตรวจสอบบนแต่ละ node แล้ว
5. ต้อง validate การ mount `keeper_config.xml` แยกระหว่าง Keeper process และ
   ClickHouse server เพื่อป้องกัน embedded Keeper/server-id conflict
6. Service-account และ S3 environment variables ต้องส่งเข้า ClickHouse containers
   ให้ครบและทดสอบจริง
7. TLS สำหรับ ClickHouse HTTP/native, interserver และ Keeper ยังต้องออกแบบ/อนุมัติ
8. Load balancer/VIP และ health-check policy ยังเป็น `TBD`
9. Production Data Sources และ Streaming topology ยังไม่มี approved Compose/IaC

จนกว่ารายการเหล่านี้จะปิดครบ ให้ถือว่าสถานะเป็น **NOT READY FOR PRODUCTION**

## 5. Host Preparation

ดำเนินการบน Host 01-03 ด้วย approved automation และเก็บ output ใน change record:

```bash
hostnamectl
timedatectl
lsblk
df -h
free -h
nproc
docker version
docker compose version
```

ตรวจ sysctl, ulimit, filesystem, mount options และ disk latency ตามมาตรฐานองค์กร
ห้ามใช้ local disk เป็น backup destination เพียงแห่งเดียว

กำหนดค่าที่ต้องได้รับอนุมัติ:

```dotenv
HOST_NODE1_IP=TBD
HOST_NODE2_IP=TBD
HOST_NODE3_IP=TBD
CLICKHOUSE_ADMIN_USER=TBD
CLICKHOUSE_ADMIN_PASSWORD=<SECRET_MANAGER_REFERENCE>
CLICKHOUSE_ETL_PASSWORD=<SECRET_MANAGER_REFERENCE>
CLICKHOUSE_BI_PASSWORD=<SECRET_MANAGER_REFERENCE>
CLICKHOUSE_API_PASSWORD=<SECRET_MANAGER_REFERENCE>
CLICKHOUSE_MONITORING_PASSWORD=<SECRET_MANAGER_REFERENCE>
CLICKHOUSE_S3_ENDPOINT=TBD
CLICKHOUSE_S3_ACCESS_KEY=<SECRET_MANAGER_REFERENCE>
CLICKHOUSE_S3_SECRET_KEY=<SECRET_MANAGER_REFERENCE>
S3_REGION=TBD
```

## 6. ติดตั้ง Portainer Management Plane

1. ติดตั้ง Portainer Server บน dedicated management host
2. เปิด UI เฉพาะ Management VPN ที่ `9443/TCP`
3. ติดตั้ง Portainer Agent บน Host 01-03 ด้วย approved pinned image
4. เปิด `9001/TCP` เฉพาะจาก Portainer Server
5. เพิ่ม environments ชื่อ `prod-node1`, `prod-node2`, `prod-keeper3`
6. ตรวจ RBAC, MFA/SSO, audit log และ backup ของ Portainer data

Compose ใน repository กำหนด Agent ด้วย profile `agent`; หากองค์กรติดตั้ง Agent
แยกด้วย automation อยู่แล้ว ห้ามเปิด profile ซ้ำ

## 7. Pre-deployment Validation

Clone approved tag/SHA ใน isolated validation workspace:

```bash
git clone --branch <APPROVED_RELEASE_TAG> --depth 1 \
  https://github.com/kingpac-dev/Enterprise-Data-Lakehouse-Platform.git
cd Enterprise-Data-Lakehouse-Platform

docker compose --env-file <APPROVED_ENV_FILE> \
  -f compose/docker-compose.prod-node1.yml config --quiet
docker compose --env-file <APPROVED_ENV_FILE> \
  -f compose/docker-compose.prod-node2.yml config --quiet
docker compose --env-file <APPROVED_ENV_FILE> \
  -f compose/docker-compose.prod-keeper3.yml config --quiet
python3 governance/policy_linter.py
```

รัน image scan และ XML parser checks ตาม CI pipeline แล้วแนบ output จริง ห้ามถือว่า
ผ่านจากเอกสารหรือผลเก่า

ตรวจ connectivity ก่อน deploy:

```bash
nc -vz <NODE1_IP> 9234
nc -vz <NODE2_IP> 9234
nc -vz <NODE3_IP> 9234
nc -vz <ENTERPRISE_S3_HOST> 443
```

รันจากทุก node ไปยังทุก peer ตาม firewall matrix

## 8. Deployment Order

ใช้ Repository URL และ approved tag/SHA เดียวกันทุก environment ห้ามใช้ mutable
branch โดยตรง

### Phase 1: Keeper quorum

1. Deploy `compose/docker-compose.prod-keeper3.yml` บน `prod-keeper3`
2. Deploy Keeper service จาก `prod-node1.yml` บน Host 01
3. Deploy Keeper service จาก `prod-node2.yml` บน Host 02
4. ตรวจว่า Keeper ทั้ง 3 members ติดต่อกันและเลือก leader สำเร็จ
5. ห้ามเริ่ม ClickHouse replicas หาก quorum ไม่ครบ

Portainer Compose จะ deploy services ในไฟล์ร่วมกันโดยปกติ ดังนั้นการแยก Keeper-only
phase ต้องใช้ approved deployment override/profile หรือเตรียม Keeper ล่วงหน้าด้วย
automation ที่ผ่าน review ห้ามแก้ Compose ad hoc ใน Portainer editor

ตรวจ Keeper จาก trusted admin host:

```bash
echo ruok | nc <NODE1_IP> 9181
echo ruok | nc <NODE2_IP> 9181
echo ruok | nc <NODE3_IP> 9181
```

เก็บผลตอบกลับจริงและตรวจ quorum/leader ผ่าน Keeper system tables หรือ approved tool

### Phase 2: ClickHouse replicas

1. Deploy approved Node 1 stack บน `prod-node1`
2. รอ ClickHouse 01 healthy และตรวจ Keeper session
3. Deploy approved Node 2 stack บน `prod-node2`
4. รอ ClickHouse 02 healthy
5. ตรวจ replicas และ replication queue ก่อนเปิด traffic

Environment variables ที่ต้องตั้งแยก:

| Variable | Node 1 | Node 2 | Node 3 |
|---|---:|---:|---:|
| `KEEPER_SERVER_ID` | `1` | `2` | `3` |
| `CLICKHOUSE_SHARD` | `1` | `1` | N/A |
| `CLICKHOUSE_REPLICA` | `1` | `2` | N/A |
| `HOST_NODE1_IP` | approved IP | ค่าเดียวกัน | ค่าเดียวกัน |
| `HOST_NODE2_IP` | approved IP | ค่าเดียวกัน | ค่าเดียวกัน |
| `HOST_NODE3_IP` | approved IP | ค่าเดียวกัน | ค่าเดียวกัน |

Secrets ของ ClickHouse/S3 ต้องเหมือนกันตาม scope ที่ออกแบบไว้ แต่ต้อง inject ผ่าน
approved secret mechanism ไม่ใช่ commit ลง repository

### Phase 3: Load balancer and traffic

ดำเนินการโดย Network/Platform owner หลัง cluster validation เท่านั้น:

1. เพิ่ม ClickHouse 01-02 เข้า internal load balancer
2. Health check ใช้ `/ping` ผ่าน approved TLS endpoint
3. เริ่มด้วย canary traffic
4. ตรวจ error rate, latency, replication queue และ resource utilization
5. เปิด traffic เต็มหลัง CAB/owner approval

## 9. Production Verification

รันบนทั้งสอง replicas:

```sql
SELECT version();
SELECT cluster, shard_num, replica_num, host_name, port
FROM system.clusters
WHERE cluster = 'cluster_1s_2r';

SELECT database, table, is_leader, is_readonly, is_session_expired,
       queue_size, absolute_delay
FROM system.replicas;

SELECT * FROM system.replication_queue
ORDER BY create_time DESC LIMIT 50;

SELECT name, type, path FROM system.disks;
SELECT policy_name, volume_name, disks FROM system.storage_policies;
```

Acceptance criteria ต้องกำหนดใน change record อย่างน้อย:

- Keeper quorum 3/3 และมี leader
- ClickHouse replicas 2/2 healthy
- `is_readonly = 0` และ `is_session_expired = 0`
- Replication queue/delay อยู่ใน approved threshold
- Enterprise S3 read/write test ผ่าน
- Query smoke test และ data reconciliation ผ่าน
- Prometheus targets/alerts ผ่าน

## 10. Backup, Restore and DR Gate

ก่อนรับ production traffic:

1. รัน backup ไป independent enterprise S3
2. บันทึก backup ID, size, duration และ checksum/manifest
3. Restore ไป isolated database/environment แบบ non-destructive
4. เปรียบเทียบ row counts และ business totals
5. บันทึก measured RPO/RTO
6. ให้ DBA/Data Owner ลงนาม

ดูขั้นตอนใน [Runbook 02: Backup and Restore](02_backup_and_restore_operations.md)
เป้าหมาย RPO `<= 1 hour` และ RTO `<= 4 hours` ยังต้องได้รับ business owner sign-off

## 11. Rollback

1. หยุด traffic promotion หรือถอด node ที่มีปัญหาออกจาก load balancer
2. เก็บ logs, system tables และ incident timestamp
3. เปลี่ยน Portainer Git reference กลับ approved tag/SHA ก่อนหน้า
4. Update เฉพาะ stack ที่ได้รับผลกระทบโดยไม่ลบ volumes
5. ตรวจ Keeper quorum, replicas, S3 และ query smoke test ใหม่

Git rollback ไม่ rollback schema/data การ destructive migration ต้องใช้ migration-specific
rollback plan และ DBA approval ห้ามใช้ `docker compose down -v`, ลบ volume หรือ drop
database เป็นวิธี rollback

## 12. Evidence and Sign-off

Change record ต้องแนบ:

- Approved architecture/IP/firewall matrix
- Compose rendered output โดย redact secrets
- Image digests และ vulnerability scan
- Container health และ Keeper quorum evidence
- ClickHouse replica/system table outputs
- S3 read/write result
- Backup/restore drill result
- Monitoring target/alert evidence
- Load/performance test result
- Approver names, timestamps และ release tag/SHA

## Handoff Contract

- **Scope & Sources Inspected:** PROD Node 1, Node 2, Keeper 3 Compose, ClickHouse/
  Keeper configs, backup runbook และ AGENTS.md
- **Assumptions & Decisions:** Production ต้องมี 3 independent failure domains,
  independent S3 และ dedicated management plane
- **Security & Operational Impact:** Network isolation, TLS, secret manager, least
  privilege, image scan และ human approval เป็น mandatory gates
- **Validation Commands & Results:** เอกสารนี้ไม่ได้ยืนยันว่า PROD validation ผ่าน;
  ต้องรันคำสั่งบน infrastructure จริงและแนบ output
- **Remaining TBDs & Residual Risks:** IP/DNS/CIDR, TLS, image digests, S3/KMS,
  load balancer, observability topology, capacity และ approved RPO/RTO
- **Human Approval Required:** CAB/Change Manager, Platform/DevOps, DBA,
  Security, Network และ Data Owner ต้องอนุมัติก่อน deploy และเปิด traffic
