# Runbook 05: Harbor Registry สำหรับ UAT และ Portainer

เอกสารนี้อธิบายการจัดเตรียม `TBD_HARBOR_FQDN` สำหรับ UAT แล้วเชื่อมต่อกับ
Portainer เพื่อให้ Git-backed Stacks pull custom images ได้

> [!IMPORTANT]
> Portainer ไม่ได้สร้าง DNS หรือ Harbor service ให้โดยอัตโนมัติ เมนู **Registries**
> ใช้ลงทะเบียน Harbor ที่ติดตั้งและเปิดใช้งานแล้วเท่านั้น

> [!CAUTION]
> ขั้นตอนนี้เป็น UAT Single Node ไม่ใช่ Harbor HA สำหรับ Production ต้องออกแบบ database,
> Redis, object storage, backup, replication และ failure domains แยกต่างหาก

## 1. Architecture และค่าที่ต้องอนุมัติ

```text
GitHub -> Jenkins/CI -> Trivy/Harbor Scanner -> TBD_HARBOR_FQDN
                                                   |
                                                   v
                                      Portainer -> UAT Docker Endpoint
```

| Parameter | UAT value |
|---|---|
| Harbor FQDN | `TBD_APPROVED_HARBOR_FQDN` |
| Harbor host IP | `TBD` |
| Harbor project | `lakehouse` |
| HTTPS port | `443` |
| HTTP port | `80` เฉพาะ redirect/ACME หากจำเป็น |
| Data path | `/srv/harbor/data` |
| TLS issuer | `TBD_CORPORATE_CA_OR_PUBLIC_CA` |
| Backup target | `TBD_INDEPENDENT_BACKUP_TARGET` |

แนะนำให้ใช้ VM/Docker host แยกจาก Portainer และ Lakehouse application host เพื่อไม่ให้
registry ซึ่งเป็น dependency ของ deployment หยุดพร้อม workload หากจำเป็นต้องใช้ host เดียว
ใน UAT ต้องยอมรับว่าไม่ใช่ HA และตรวจว่า ports `80/443` ไม่ชนกับบริการอื่น

ขั้นต่ำของ Harbor คือ 2 CPU, RAM 4 GB และ disk 40 GB; ขนาดแนะนำคือ 4 CPU, RAM 8 GB
และ disk 160 GB

## 2. สร้าง DNS บน Cloudflare และ Firewall

Zone `kingpac-th.com` บริหารด้วย Cloudflare แต่ Cloudflare ทำหน้าที่ DNS/Proxy เท่านั้น
ไม่ใช่เครื่องที่รัน Harbor ให้เลือกวิธีตามเส้นทาง network จริงก่อนสร้าง record:

### 2.1 Harbor มี Public IP หรือ Public NAT

ใน Cloudflare Dashboard ไปที่ **Websites > kingpac-th.com > DNS > Records > Add record**
แล้วกำหนด:

| Field | Value |
|---|---|
| Type | `A` |
| Name | `harbor` |
| IPv4 address | `<HARBOR_PUBLIC_IP_OR_NAT_IP>` |
| Proxy status | **DNS only** (เมฆสีเทา) |
| TTL | `Auto` หรือตามมาตรฐานองค์กร |

ค่า `Name=harbor` จะได้ FQDN เป็น `TBD_HARBOR_FQDN` โดยใช้ **DNS only** เป็นค่าเริ่มต้น
สำหรับ OCI/Docker Registry เนื่องจากการ push image เป็น request ขนาดใหญ่และอาจใช้เวลานาน
Cloudflare Proxy มี request-size limit และ timeout ตาม plan จึงต้องทดสอบและอนุมัติแยกต่างหาก
หากองค์กรต้องการเปิด Proxy (เมฆสีส้ม) หรือ Cloudflare Tunnel จริง ห้ามถือว่าสามารถใช้กับ
registry ได้โดยอัตโนมัติ ต้องผ่านการทดสอบ push/pull image ขนาดจริงและทบทวนข้อจำกัดของ plan ก่อน

> [!WARNING]
> DNS-only จะเปิดเผย Public IP ของ Harbor origin จึงต้องจำกัด inbound `443/tcp` ที่ firewall
> เฉพาะ CI runner, Portainer/Docker endpoints และ Admin VPN ที่ได้รับอนุมัติ ห้ามพึ่งการซ่อน IP เป็นมาตรการรักษาความปลอดภัย

### 2.2 Harbor ใช้ Private IP เช่น `192.168.10.188`

Public Cloudflare DNS ไม่ได้สร้าง route ไปยัง private subnet ให้ หาก Jenkins, Portainer และ Docker host
เข้าถึงเครือข่ายนี้ผ่าน LAN/VPN ให้ใช้ **internal/split-horizon DNS** ขององค์กร:

```text
Type: A
Name: TBD_HARBOR_FQDN
Value: <HARBOR_PRIVATE_IP>
Scope: corporate LAN/VPN only
```

อย่าใส่ `192.168.10.188` ลง Cloudflare public DNS แล้วคาดว่าจะเข้าถึงจาก Internet ได้
เพราะ RFC1918 address ไม่สามารถ route ผ่าน Internet ได้ หากต้องการให้บริการจากภายนอก ให้ Network/Security
อนุมัติ Public NAT/reverse proxy หรือ Cloudflare private-network design ก่อน โดยคงค่า IP จริงเป็น `TBD`
จนกว่าจะได้รับอนุมัติ

เปิด firewall อย่างน้อย:

| Source | Destination | Port | Purpose |
|---|---|---:|---|
| Jenkins/CI runners | Harbor host | `443/tcp` | Push images |
| Portainer/UAT Docker endpoint | Harbor host | `443/tcp` | Pull images |
| Admin VPN | Harbor host | `443/tcp` | Harbor UI/API |

ตรวจ DNS และ TLS routing:

```bash
getent hosts TBD_HARBOR_FQDN
curl -fsS https://TBD_HARBOR_FQDN/api/v2.0/ping
openssl s_client -connect TBD_HARBOR_FQDN:443 \
  -servername TBD_HARBOR_FQDN </dev/null
```

รันคำสั่งจากทั้ง Jenkins runner และ UAT Docker endpoint เพื่อยืนยันว่า DNS resolution และ routing
มองเห็นเส้นทางเดียวกับที่ใช้ push/pull จริง

## 3. เตรียม Harbor Host

ใช้ Ubuntu 24 LTS ที่ hardened และ NTP synchronized พร้อม Docker Engine, Compose V2
และ OpenSSL:

```bash
sudo docker version
sudo docker compose version
openssl version
df -h /srv
free -h
```

สร้าง data/config directories:

```bash
sudo install -d -m 0750 /opt/harbor
sudo install -d -m 0750 /srv/harbor/data
sudo install -d -m 0750 /etc/harbor/tls
```

## 4. ออกและติดตั้ง TLS Certificate

ขอ certificate จาก Corporate PKI หรือ public CA โดย certificate ต้องมี SAN:

```text
DNS:TBD_HARBOR_FQDN
```

เพราะแนวทางหลักใช้ DNS-only ซึ่ง client เชื่อมต่อ Harbor โดยตรง ให้ใช้ certificate จาก public CA
หรือ Corporate CA ที่ติดตั้ง trust chain ไว้บน Jenkins, Portainer และ Docker hosts แล้ว
**ห้ามใช้ Cloudflare Origin CA กับ DNS-only** เพราะ certificate ชนิดนี้ออกแบบให้ Cloudflare Proxy
เป็นผู้เชื่อมต่อ origin และ Docker client ทั่วไปจะไม่เชื่อถือโดยอัตโนมัติ

ติดตั้ง certificate และ private key โดยไม่ commit ลง Git:

```bash
sudo install -m 0644 <APPROVED_FULLCHAIN_FILE> \
  /etc/harbor/tls/fullchain.pem
sudo install -m 0600 <APPROVED_PRIVATE_KEY_FILE> \
  /etc/harbor/tls/privkey.pem
```

ห้ามใช้ HTTP/insecure registry สำหรับระบบที่เชื่อมต่อ network องค์กร

## 5. ดาวน์โหลดและติดตั้ง Harbor

เลือก Harbor GA patch release ที่ผ่านการอนุมัติและตรวจ release signature/checksum จาก
official release page ก่อนติดตั้ง ตัวอย่างใช้ `v2.15.2`:

```bash
cd /opt/harbor
HARBOR_VERSION=2.15.2
sudo curl -fLO \
  "https://github.com/goharbor/harbor/releases/download/v${HARBOR_VERSION}/harbor-online-installer-v${HARBOR_VERSION}.tgz"
sudo tar -xzf "harbor-online-installer-v${HARBOR_VERSION}.tgz" --strip-components=1
sudo cp harbor.yml.tmpl harbor.yml
```

แก้ `/opt/harbor/harbor.yml` โดยใช้ secret จริงที่มาจาก approved secret manager:

```yaml
hostname: TBD_HARBOR_FQDN

http:
  port: 80

https:
  port: 443
  certificate: /etc/harbor/tls/fullchain.pem
  private_key: /etc/harbor/tls/privkey.pem

harbor_admin_password: <STRONG_SECRET_FROM_SECRET_MANAGER>

database:
  password: <STRONG_DATABASE_SECRET_FROM_SECRET_MANAGER>

data_volume: /srv/harbor/data
```

ห้ามนำ `harbor.yml` ที่มี secrets ไป commit ลง repository จากนั้นติดตั้งพร้อม Trivy:

```bash
cd /opt/harbor
sudo ./install.sh --with-trivy
sudo docker compose ps
```

ตรวจว่า UI/API ตอบสนองและ TLS ถูกต้อง:

```bash
curl -fsS https://TBD_HARBOR_FQDN/api/v2.0/ping
sudo docker login TBD_HARBOR_FQDN
```

## 6. สร้าง Project และ Robot Accounts

1. เปิด `https://TBD_HARBOR_FQDN`
2. Login ด้วย Harbor administrator แล้ว rotate bootstrap password หากยังไม่ได้ทำ
3. ไปที่ **Projects > New Project**
4. สร้าง private project ชื่อ `lakehouse`
5. ไปที่ **lakehouse > Robot Accounts** แล้วสร้างอย่างน้อยสองบัญชี:

| Robot account | Permissions | Consumer |
|---|---|---|
| `ci-push` | Pull + Push repositories, scan/read ตามนโยบาย | Jenkins/CI |
| `portainer-pull` | Pull repositories เท่านั้น | Portainer |

กำหนดวันหมดอายุตามนโยบายองค์กรและบันทึก secret ลง secret manager ทันที Harbor จะแสดง
robot secret ตอนสร้างเพียงครั้งเดียว ห้ามบันทึกไฟล์ credential ลง Git

## 7. Build และ Push Lakehouse Images

บน approved CI runner หรือ controlled build host ให้กำหนด immutable release tag:

```bash
REGISTRY=TBD_HARBOR_FQDN
PROJECT=lakehouse
RELEASE_TAG=<APPROVED_RELEASE_TAG>

export CLICKHOUSE_UAT_IMAGE="${REGISTRY}/${PROJECT}/clickhouse-uat:${RELEASE_TAG}"
export DBT_RUNNER_UAT_IMAGE="${REGISTRY}/${PROJECT}/dbt-runner-uat:${RELEASE_TAG}"
export SERVING_API_UAT_IMAGE="${REGISTRY}/${PROJECT}/serving-api-uat:${RELEASE_TAG}"
export SOURCE_MSSQL_INIT_IMAGE="${REGISTRY}/${PROJECT}/source-mssql-init:${RELEASE_TAG}"
export SOURCE_MONGODB_UAT_IMAGE="${REGISTRY}/${PROJECT}/source-mongodb:${RELEASE_TAG}"
export PROMETHEUS_UAT_IMAGE="${REGISTRY}/${PROJECT}/prometheus-uat:${RELEASE_TAG}"
export GRAFANA_UAT_IMAGE="${REGISTRY}/${PROJECT}/grafana-uat:${RELEASE_TAG}"
export LOKI_UAT_IMAGE="${REGISTRY}/${PROJECT}/loki-uat:${RELEASE_TAG}"

docker login "${REGISTRY}"
docker compose -f compose/docker-compose.uat-build.yml build --pull
docker compose -f compose/docker-compose.uat-build.yml push
```

Jenkins ต้องใช้ robot account `ci-push`; ห้ามใช้ Harbor admin account ตรวจ Trivy results
และอนุมัติ promotion ก่อนให้ Portainer pull release tag

## 8. เพิ่ม Harbor ใน Portainer

ใน Portainer ไปที่ **Registries > Add registry > Custom registry** แล้วกำหนด:

```text
Name: harbor-kingpac
Registry URL: TBD_HARBOR_FQDN
Authentication: enabled
Username: <HARBOR_PORTAINER_PULL_ROBOT_USERNAME>
Password: <HARBOR_PORTAINER_PULL_ROBOT_SECRET>
```

ใช้ robot account `portainer-pull` เท่านั้น เปิด TLS verification และห้ามเลือก skip TLS
verification หากใช้ Corporate CA ต้องติดตั้ง CA chain ให้ Portainer Server, Agent และ Docker
daemon บน UAT endpoint เชื่อถือก่อน

## 9. ตั้งค่า Portainer Git Stacks

ใช้ image variables ที่อ้าง release เดียวกัน ตัวอย่าง Core:

```dotenv
CLICKHOUSE_UAT_IMAGE=TBD_HARBOR_FQDN/lakehouse/clickhouse-uat:<APPROVED_RELEASE_TAG>
DBT_RUNNER_UAT_IMAGE=TBD_HARBOR_FQDN/lakehouse/dbt-runner-uat:<APPROVED_RELEASE_TAG>
SERVING_API_UAT_IMAGE=TBD_HARBOR_FQDN/lakehouse/serving-api-uat:<APPROVED_RELEASE_TAG>
```

ตั้งค่า Stacks อื่นตาม Runbook 01 และใช้ immutable tag/digest เดียวกัน ห้ามใช้ `latest`

## 10. Acceptance Checks

รันจาก UAT Docker endpoint:

```bash
getent hosts TBD_HARBOR_FQDN
curl -fsS https://TBD_HARBOR_FQDN/api/v2.0/ping
sudo docker pull \
  TBD_HARBOR_FQDN/lakehouse/clickhouse-uat:<APPROVED_RELEASE_TAG>
```

ตรวจใน Harbor UI ว่ามี scan report, immutable release tag และ audit log ก่อน Deploy
Portainer Stack เก็บผลจริงไว้ใน change record ห้ามรายงานว่าสำเร็จหากยังไม่ได้รัน

## 11. Backup และข้อจำกัด

- สำรอง `/srv/harbor/data`, Harbor database และ `/opt/harbor/harbor.yml` แบบเข้ารหัสไปยัง
  independent backup target
- ทดสอบ non-destructive restore drill ก่อนถือว่า backup ใช้งานได้
- RPO/RTO, retention, project quota และ garbage-collection schedule เป็น `TBD` จนกว่า
  Business Owner/Security/Platform จะอนุมัติ
- Harbor UAT Single Node หยุดทำงานทันทีเมื่อ host/disk/network ล้มเหลว

## 12. เอกสารอ้างอิง

- [Cloudflare: Manage DNS records](https://developers.cloudflare.com/dns/manage-dns-records/how-to/create-dns-records/)
- [Cloudflare: Proxy status, request limits และ timeouts](https://developers.cloudflare.com/dns/proxy-status/)
- [Cloudflare: Origin CA certificate limitations](https://developers.cloudflare.com/ssl/origin-configuration/origin-ca/)

## Handoff Contract

- **Scope & Sources Inspected:** Harbor installer/configuration, Cloudflare DNS/proxy behavior,
  TLS, project/robot accounts, Portainer custom registry และ UAT image flow
- **Assumptions & Decisions:** Ubuntu 24 LTS, Harbor UAT Single Node, HTTPS only, Cloudflare
  DNS-only สำหรับ public origin หรือ internal split DNS สำหรับ private origin, private project
  `lakehouse` และ immutable release tags
- **Security & Operational Impact:** Secrets อยู่ใน secret manager; Portainer ใช้ pull-only
  robot; Jenkins ใช้ push robot; DNS-only ต้องจำกัด origin ด้วย firewall; ห้าม commit
  `harbor.yml` หรือ TLS private key
- **Validation Commands & Results:** ต้องแนบ DNS, TLS, Harbor API, image push/pull, scan
  และ restore-drill outputs จาก UAT host ใน change record
- **Remaining TBDs & Residual Risks:** Public/NAT หรือ private IP และ DNS route, CA issuer,
  backup target, quotas, retention, GC schedule และ business-approved RPO/RTO
- **Human Approval Required:** DNS/Network, Security/PKI, Platform/DevOps และ Change Owner
  ต้องอนุมัติก่อนเปิดใช้งาน
