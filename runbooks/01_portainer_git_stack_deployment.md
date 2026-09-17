# Runbook 01: Deploy UAT Single Node ด้วย Portainer Git-backed Stacks

เอกสารนี้สำหรับ **UAT เท่านั้น** สำหรับ Production ให้ใช้
[Runbook 04: Production Multi-Host Deployment](04_portainer_prod_deployment.md)
ดูภาพรวมระบบที่ [UAT Architecture Design](../docs/architecture/UAT_ARCHITECTURE.md)

## 1. ขอบเขต

คู่มือนี้ใช้ติดตั้ง Enterprise Data Lakehouse Platform บน Ubuntu 24 LTS เครื่องเดียว
และบริหารด้วย Portainer Git-backed Stacks โดยแบ่งเป็น 4 stacks:

| ลำดับ | Stack | Compose path | บริการหลัก |
|---:|---|---|---|
| 1 | `lakehouse-uat-core` | `compose/docker-compose.dev.yml` | ClickHouse, MinIO, dbt, Serving API |
| 2 | `lakehouse-uat-datasources` | `compose/docker-compose.datasources.yml` | PostgreSQL, MySQL, SQL Server, MongoDB |
| 3 | `lakehouse-uat-streaming` | `compose/docker-compose.streaming.yml` | Redpanda, Redpanda Console |
| 4 | `lakehouse-uat-observability` | `compose/docker-compose.observability.yml` | Prometheus, Grafana, Loki |

> [!CAUTION]
> นี่คือ UAT Single Node ไม่ใช่ High Availability หาก host, disk หรือ Docker Engine
> ขัดข้อง ทุก stack จะได้รับผลกระทบพร้อมกัน

## 2. Prerequisites

- Ubuntu Server 24 LTS พร้อม static IP/DNS: `TBD`
- CPU อย่างน้อย 12 cores, RAM อย่างน้อย 24 GB (แนะนำ 32 GB)
- SSD/NVMe ว่างอย่างน้อย 300 GB
- DNS, NTP และ timezone ถูกต้อง
- Host เข้าถึง Git repository และ container registries ได้
- Firewall อนุญาตเฉพาะ source CIDR ที่ได้รับอนุมัติ
- ใช้ synthetic หรือ masked UAT data เท่านั้น
- เตรียม secrets แยกสำหรับทุก service และห้าม commit ลง Git

```bash
hostnamectl
timedatectl
df -h
free -h
nproc
```

## 3. ติดตั้ง Docker Engine และ Compose V2

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" |
  sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker version
sudo docker compose version
```

กำหนด Docker log rotation:

```bash
sudo install -d -m 0755 /etc/docker
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": {"max-size": "100m", "max-file": "5"}
}
EOF
sudo systemctl restart docker
sudo systemctl is-active docker
```

## 4. ติดตั้ง Portainer แยกจาก Application Stacks

```bash
sudo docker volume create portainer_data
sudo docker run -d \
  --name portainer \
  --restart=always \
  -p 9443:9443 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:2.21.0
```

เข้า `https://<UAT_HOST>:9443` แล้วสร้าง administrator, เลือก Local Docker
environment และจำกัด port `9443` ให้เข้าถึงจาก Management VPN/admin CIDR เท่านั้น
ไม่ต้องเปิด Portainer HTTP port `9000`

## 5. Validate Release ก่อน Deploy

```bash
git clone https://github.com/kingpac-dev/Enterprise-Data-Lakehouse-Platform.git
cd Enterprise-Data-Lakehouse-Platform
cp .env.example .env
# เปลี่ยน placeholder secrets ใน .env ก่อน validate

for file in compose/*.yml; do
  docker compose --env-file .env -f "$file" config --quiet
done
python3 governance/policy_linter.py
```

ทดสอบให้ Docker host ดึง images จาก registries ได้ก่อนกด Deploy:

```bash
sudo docker pull quay.io/minio/minio:RELEASE.2024-08-17T01-24-54Z@sha256:6f23072e3e222e64fe6f86b31a7f7aca971e5129e55cbccef649b109b8e651a1
sudo docker pull quay.io/minio/mc:RELEASE.2024-08-13T05-33-17Z@sha256:07c08763869bb18306d6f33a7e887c42211b1585a63c9098c9cf28b1b45b19aa
sudo docker pull clickhouse/clickhouse-server:26.8
sudo docker pull rustfs/rustfs:1.0.0@sha256:8cc9801755448b71a786705ce76692c77e14936cccd87cf2fc31842e58f4d1ff
```

หากองค์กรบังคับใช้ Harbor/private registry ให้ mirror images ที่ผ่านการ scan แล้ว
และกำหนด `MINIO_IMAGE`/`MINIO_MC_IMAGE` เป็น Harbor references แทน ห้ามปิด TLS
verification เพื่อแก้ปัญหาการ pull image

ใช้ approved release tag หรือ commit SHA ไม่ควร deploy จาก `main` โดยตรงหากยังไม่มี
CI และ human approval gate

### Build custom UAT images ก่อนเข้า Portainer

ไฟล์ Compose ที่ใช้ deploy ผ่าน Portainer ไม่มี `build:` เพื่อหลีกเลี่ยงการส่ง BuildKit/gRPC
ผ่าน Portainer Agent ให้ build บน Docker endpoint host โดยตรง หรือ build ใน CI แล้ว push
เข้า Harbor ก่อน deploy ห้ามเลือก `compose/docker-compose.uat-build.yml` เป็น Stack compose path

สำหรับ UAT host ที่ยังไม่มี Harbor ให้ checkout approved reference บน **เครื่อง Docker endpoint
เดียวกับที่ Portainer environment ชี้อยู่** แล้ว build local images:

```bash
git fetch --tags
git checkout <APPROVED_RELEASE_TAG_OR_SHA>

sudo docker buildx inspect --bootstrap
sudo docker compose --env-file .env.example \
  -f compose/docker-compose.uat-build.yml build --pull

sudo docker image inspect \
  lakehouse/clickhouse-uat:26.8 \
  lakehouse/source-mssql-init:2022-CU16 \
  lakehouse/source-mongodb:8.0.4 \
  lakehouse/prometheus-uat:2.54.0 \
  lakehouse/grafana-uat:11.1.4 \
  lakehouse/loki-uat:3.1.1 >/dev/null
```

เมื่อใช้ local images ให้กำหนด `UAT_CUSTOM_IMAGE_PULL_POLICY=never` ในแต่ละ Portainer Stack
เพื่อไม่ให้ Portainer พยายาม pull ชื่อ `lakehouse/*` จาก public registry หากใช้ Harbor ให้กำหนด
เป็น `missing` และใช้ immutable tag/digest ที่เปลี่ยนทุก release

ถ้าจะ deploy เฉพาะ Observability สามารถ build เฉพาะสาม images ได้:

```bash
sudo docker compose --env-file .env.example \
  -f compose/docker-compose.uat-build.yml build --pull \
  prometheus-uat grafana-uat loki-uat
```

แนวทางที่แนะนำสำหรับงานองค์กรคือให้ Jenkins build, Trivy scan และ push images ด้วย
immutable release tag/digest เข้า Harbor จากนั้นเพิ่ม Harbor ใน **Portainer > Registries** และ
กำหนดตัวแปร `*_UAT_IMAGE` เป็น Harbor reference ห้ามเก็บ registry password ใน Git

## 6. Deploy Stack 1: UAT Core

ใน Portainer ไปที่ **Environments > Local > Stacks > Add stack > Repository**:

```text
Name: lakehouse-uat-core
Repository URL: https://github.com/kingpac-dev/Enterprise-Data-Lakehouse-Platform.git
Repository reference: refs/tags/<APPROVED_RELEASE_TAG>
Compose path: compose/docker-compose.dev.yml
```

เพิ่ม Environment variables:

```dotenv
ENVIRONMENT=uat
INTEGRATION_NETWORK=lakehouse-uat-integration
OBSERVABILITY_NETWORK=lakehouse-uat-observability
CLICKHOUSE_PORT_HTTP=18123
CLICKHOUSE_PORT_NATIVE=19000
CLICKHOUSE_PORT_PROMETHEUS=19363
UAT_CUSTOM_IMAGE_PULL_POLICY=never
CLICKHOUSE_UAT_IMAGE=lakehouse/clickhouse-uat:26.8
CLICKHOUSE_ADMIN_USER=admin
CLICKHOUSE_ADMIN_PASSWORD=<STRONG_SECRET>
CLICKHOUSE_ETL_PASSWORD=<STRONG_SECRET>
CLICKHOUSE_BI_PASSWORD=<STRONG_SECRET>
CLICKHOUSE_API_PASSWORD=<STRONG_SECRET>
CLICKHOUSE_MONITORING_PASSWORD=<STRONG_SECRET>
S3_PORT=19090
MINIO_CONSOLE_PORT=19091
MINIO_IMAGE=quay.io/minio/minio:RELEASE.2024-08-17T01-24-54Z@sha256:6f23072e3e222e64fe6f86b31a7f7aca971e5129e55cbccef649b109b8e651a1
MINIO_MC_IMAGE=quay.io/minio/mc:RELEASE.2024-08-13T05-33-17Z@sha256:07c08763869bb18306d6f33a7e887c42211b1585a63c9098c9cf28b1b45b19aa
S3_BUCKET_LAKE=enterprise-data-lake-uat
S3_ACCESS_KEY=<STRONG_ACCESS_KEY>
S3_SECRET_KEY=<STRONG_SECRET>
S3_REGION=us-east-1
CLICKHOUSE_CPU_LIMIT=4
CLICKHOUSE_MEMORY_LIMIT=8G
CLICKHOUSE_MEMORY_RESERVATION=4G
SERVING_API_PORT=18000
SERVING_API_UAT_IMAGE=lakehouse/serving-api-uat:1.0.0
```

แทนค่าทุก `<STRONG_SECRET>` และ `<STRONG_ACCESS_KEY>` ด้วยค่าจริงก่อน Deploy
ห้ามคัดลอกเครื่องหมาย `<` และ `>` ไปใช้เป็นส่วนหนึ่งของรหัสผ่าน

ถ้าต้องการ Serving API ตั้งแต่แรก ให้เพิ่ม `COMPOSE_PROFILES=api` จากนั้นกด
**Deploy the stack** และตรวจว่า MinIO/ClickHouse เป็น `healthy`, `minio-init`
จบด้วย exit code `0` และ Serving API เป็น `running` หากเปิด profile

### Optional: เปิด RustFS เพิ่มใน UAT Core

RustFS เป็น S3-compatible storage เพิ่มเติมและไม่แทน MinIO อัตโนมัติ ให้เพิ่ม:

```dotenv
COMPOSE_PROFILES=api,rustfs
RUSTFS_ENABLED=true
RUSTFS_IMAGE=rustfs/rustfs:1.0.0@sha256:8cc9801755448b71a786705ce76692c77e14936cccd87cf2fc31842e58f4d1ff
RUSTFS_PORT=19094
RUSTFS_CONSOLE_PORT=19095
RUSTFS_REGION=us-east-1
RUSTFS_BUCKET_LAKE=enterprise-data-lake-rustfs
RUSTFS_ACCESS_KEY=<STRONG_UNIQUE_ACCESS_KEY>
RUSTFS_SECRET_KEY=<STRONG_UNIQUE_SECRET>
RUSTFS_CPU_LIMIT=2
RUSTFS_MEMORY_LIMIT=2G
```

หลัง deploy ตรวจ `lakehouse-rustfs` เป็น `healthy` และ `lakehouse-rustfs-init`
จบด้วย exit code `0` จากนั้นทดสอบ:

```bash
curl -fsS http://<UAT_HOST>:19094/health/ready
curl -fsS http://<UAT_HOST>:19095/rustfs/console/health
```

หากต้องการให้ ClickHouse `s3_cold` ใช้ RustFS แทน MinIO ให้เพิ่มตัวแปรต่อไปนี้
ด้วย credential ชุดเดียวกับ RustFS แล้ว Update Stack และ restart ClickHouse หลัง
RustFS healthy:

```dotenv
CLICKHOUSE_S3_ENDPOINT=http://rustfs:9000/enterprise-data-lake-rustfs/clickhouse_data/
CLICKHOUSE_S3_ACCESS_KEY=<RUSTFS_ACCESS_KEY_VALUE>
CLICKHOUSE_S3_SECRET_KEY=<RUSTFS_SECRET_KEY_VALUE>
```

ห้ามใช้ MinIO และ RustFS เป็นสำเนากันโดยถือว่าเป็น backup จนกว่าจะมี replication,
retention และ restore drill ที่ผ่านการตรวจจริง

ตรวจ networks ที่ Core เป็นผู้สร้าง:

```bash
sudo docker network inspect lakehouse-uat-integration >/dev/null
sudo docker network inspect lakehouse-uat-observability >/dev/null
```

ห้าม deploy stacks ถัดไปจนกว่าสอง networks นี้จะมีอยู่จริง

## 7. Deploy Stack 2: UAT Data Sources

```text
Name: lakehouse-uat-datasources
Repository reference: ใช้ tag/SHA เดียวกับ Core
Compose path: compose/docker-compose.datasources.yml
```

Environment variables:

```dotenv
INTEGRATION_NETWORK=lakehouse-uat-integration
UAT_CUSTOM_IMAGE_PULL_POLICY=never
SOURCE_POSTGRES_PORT=15432
SOURCE_POSTGRES_DB=source_uat
SOURCE_POSTGRES_USER=source_app
SOURCE_POSTGRES_PASSWORD=<STRONG_SECRET>
SOURCE_MYSQL_PORT=13306
SOURCE_MYSQL_DB=source_uat
SOURCE_MYSQL_USER=source_app
SOURCE_MYSQL_PASSWORD=<STRONG_SECRET>
SOURCE_MYSQL_ROOT_PASSWORD=<STRONG_ROOT_SECRET>
SOURCE_MSSQL_PORT=11433
SOURCE_MSSQL_EDITION=Developer
SOURCE_MSSQL_SA_PASSWORD=<STRONG_SA_SECRET>
SOURCE_MSSQL_DB=source_uat
SOURCE_MSSQL_USER=source_app
SOURCE_MSSQL_PASSWORD=<STRONG_APP_SECRET>
SOURCE_MSSQL_INIT_IMAGE=lakehouse/source-mssql-init:2022-CU16
SOURCE_MONGODB_PORT=17017
SOURCE_MONGODB_DB=source_uat
SOURCE_MONGODB_ROOT_USER=mongo_admin
SOURCE_MONGODB_ROOT_PASSWORD=<STRONG_ROOT_SECRET>
SOURCE_MONGODB_USER=source_app
SOURCE_MONGODB_PASSWORD=<STRONG_APP_SECRET>
SOURCE_MONGODB_UAT_IMAGE=lakehouse/source-mongodb:8.0.4
```

กด **Deploy the stack** แล้วตรวจ PostgreSQL, MySQL, SQL Server และ MongoDB เป็น
`healthy`; `source-mssql-init` ต้องจบด้วย exit code `0`

Internal endpoints สำหรับ ingestion:

```text
source-postgres:5432
source-mysql:3306
source-mssql:1433
source-mongodb:27017
```

SQL Server initializer สร้าง database และ non-SA user ส่วน MongoDB application
user ถูกสร้างเมื่อ volume เริ่มต้นครั้งแรก การแก้ secret ใน Portainer ภายหลังไม่ใช่
การ rotate credential ใน database

## 8. Deploy Stack 3: UAT Streaming

```text
Name: lakehouse-uat-streaming
Repository reference: ใช้ tag/SHA เดียวกับ Core
Compose path: compose/docker-compose.streaming.yml
```

```dotenv
INTEGRATION_NETWORK=lakehouse-uat-integration
REDPANDA_ADVERTISED_HOST=<UAT_DNS_OR_IP>
REDPANDA_PORT_KAFKA=19092
REDPANDA_PORT_ADMIN=19644
REDPANDA_CONSOLE_PORT=18088
```

`REDPANDA_ADVERTISED_HOST` ต้องเป็น IP/DNS ที่ external Kafka clients resolve ได้จริง
ห้ามปล่อยเป็น `localhost` หรือ `TBD` จากนั้น deploy และรอให้ Redpanda เป็น `healthy`

หาก Portainer แสดง `dependency failed to start: container lakehouse-redpanda is
unhealthy` ให้ตรวจที่ Docker host:

```bash
sudo docker logs --tail 200 lakehouse-redpanda
sudo docker inspect --format '{{json .State.Health}}' lakehouse-redpanda
sudo docker exec lakehouse-redpanda rpk cluster info
sudo docker exec lakehouse-redpanda rpk cluster health
```

ผลที่ต้องการคือ `Healthy: true`, ไม่มี nodes down, leaderless partitions หรือ
under-replicated partitions Health check ใน Compose ใช้
`rpk cluster health --exit-when-healthy` และไม่ parse ตัวอักษรจาก output

หลังแก้ Compose ให้ commit/push approved reference แล้วกด **Update the stack**
ไม่จำเป็นต้องลบ `redpanda_data` volume สำหรับปัญหา health check นี้

## 9. Deploy Stack 4: UAT Observability

```text
Name: lakehouse-uat-observability
Repository reference: ใช้ tag/SHA เดียวกับ Core
Compose path: compose/docker-compose.observability.yml
```

```dotenv
OBSERVABILITY_NETWORK=lakehouse-uat-observability
UAT_CUSTOM_IMAGE_PULL_POLICY=never
PROMETHEUS_UAT_IMAGE=lakehouse/prometheus-uat:2.54.0
GRAFANA_UAT_IMAGE=lakehouse/grafana-uat:11.1.4
LOKI_UAT_IMAGE=lakehouse/loki-uat:3.1.1
PROMETHEUS_PORT=19093
GRAFANA_PORT=13000
LOKI_PORT=13100
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=<STRONG_SECRET>
```

Compose ชุด UAT จะ pull หรือใช้ images ที่ build ไว้บน endpoint host แล้ว จึงไม่ส่ง build
ผ่าน Portainer Agent ไม่ต้องเพิ่มไฟล์ใน **Additional paths** และไม่ใช้ relative bind mount
สำหรับ config เมื่อ deploy ผ่าน Portainer Git Stack

Deploy แล้วตรวจ Prometheus, Grafana และ Loki เป็น `running` จากนั้นเปิด Prometheus
**Status > Targets** และยืนยันว่า `clickhouse:9363` กับ `minio:9000` เป็น `UP`

หากเคยพบ error ลักษณะนี้:

```text
error mounting "/data/compose/.../monitoring/loki/loki-config.yml"
to "/etc/loki/local-config.yaml": not a directory
```

สาเหตุคือ repository อยู่ใน filesystem ของ Portainer container แต่ Docker daemon พยายาม
resolve relative bind mount บน host ทำให้ source file กลายเป็น directory หรือหาไม่พบ ให้ใช้
release ที่มี custom image แล้วกด **Update the stack** ไม่ต้องสร้าง path ใต้ `/data/compose`
ด้วยตนเอง และไม่ต้องลบ named volumes เพื่อแก้ error นี้

หากพบ error ต่อไปนี้ในขั้น build:

```text
listing workers for Build: ... http2: frame too large,
note that the frame header looked like an HTTP/1.1 header
```

แสดงว่า BuildKit/gRPC ถูกส่งผ่าน Portainer Agent/proxy แล้วได้รับ HTTP/1.1 response ให้ยืนยันว่า
Stack compose path เป็น `compose/docker-compose.observability.yml` ซึ่งไม่มี `build:` จากนั้น
build images บน endpoint host ตามหัวข้อ **Build custom UAT images ก่อนเข้า Portainer** หรือใช้
images จาก Harbor ไม่แนะนำให้ตั้ง `DOCKER_BUILDKIT=0` เป็นวิธีถาวร เพราะเป็นเพียง workaround
ที่ปิด build backend รุ่นปัจจุบันและไม่แก้ agent/proxy configuration

## 10. ตรวจสอบหลัง Deploy

```bash
curl -fsS http://<UAT_HOST>:18123/ping
curl -fsS http://<UAT_HOST>:19090/minio/health/ready
curl -fsS http://<UAT_HOST>:19093/-/healthy
curl -fsS http://<UAT_HOST>:13000/api/health

sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
sudo docker network inspect lakehouse-uat-integration
sudo docker network inspect lakehouse-uat-observability
```

ตรวจ ClickHouse ด้วย client ที่รับ password แบบ interactive:

```sql
SELECT version();
SELECT name FROM system.databases
WHERE name IN ('raw', 'core', 'mart', 'serving') ORDER BY name;
SELECT name, type FROM system.disks;
SELECT policy_name, volume_name, disks FROM system.storage_policies;
```

รัน smoke test โดยใช้ approved environment file:

```bash
set -a
. ./.env
set +a
python3 scripts/smoke_test.py
```

เก็บ output จริงเป็น UAT evidence ห้ามรายงานว่าผ่านหากไม่ได้รันคำสั่ง

## 11. External Port Allowlist

| Service | Host port | ขอบเขตที่แนะนำ |
|---|---:|---|
| Portainer HTTPS | `9443` | Management VPN |
| ClickHouse HTTP/Native | `18123`, `19000` | Application, BI, DBA trusted CIDR |
| MinIO API/Console | `19090`, `19091` | ETL CIDR / Admin CIDR |
| RustFS API/Console | `19094`, `19095` | ETL CIDR / Admin CIDR |
| Serving API | `18000` | TLS reverse proxy |
| PostgreSQL/MySQL | `15432`, `13306` | UAT client CIDR |
| SQL Server/MongoDB | `11433`, `17017` | UAT client CIDR |
| Kafka/Admin/Console | `19092`, `19644`, `18088` | Client/Admin CIDR |
| Prometheus/Grafana/Loki | `19093`, `13000`, `13100` | Monitoring/User CIDR |

การเปลี่ยนเลข port ไม่ใช่ security control ต้องใช้ firewall, VPN, TLS และ
least-privilege accounts ร่วมกัน

## 12. Update และ Rollback

Update:

1. ให้ CI ตรวจ Compose, policy และ image scan
2. เปลี่ยน Repository reference เป็น approved tag/SHA ใหม่
3. ตรวจ environment variables ว่าไม่มี placeholder
4. กด **Update the stack** และรัน health/smoke tests ใหม่
5. ไม่เปิด automatic polling จนกว่าจะมี CI approval gate

Rollback:

1. เก็บ logs และหยุด rollout
2. เปลี่ยน Repository reference กลับ approved tag/SHA ก่อนหน้า
3. Update stack โดยไม่เลือกการลบ volumes
4. รัน health checks และ smoke test อีกครั้ง

Git rollback ไม่ได้ rollback schema หรือข้อมูล ห้ามลบ named volumes เพื่อแก้ deployment
และ destructive migration ต้องมี DBA/Data Owner approval

## 13. ลำดับการหยุดระบบ

หยุดย้อนลำดับ: Observability > Streaming > Data Sources > Core อย่าลบ Core ก่อน
dependent stacks เพราะ Core เป็นเจ้าของ shared networks และห้าม remove volumes หากไม่มี
written approval พร้อม verified backup/restore evidence

## Handoff Contract

- **Scope & Sources Inspected:** UAT Core, Data Sources, Streaming, Observability,
  environment template, monitoring configuration และ governance policy
- **Assumptions & Decisions:** Ubuntu 24 LTS, Docker Compose V2, Git-backed Stacks,
  UAT Single Node และ masked/synthetic data
- **Security & Operational Impact:** Secrets อยู่ใน Portainer; external ports จำกัด
  ด้วย firewall/VPN/TLS; application accounts ใช้ least privilege
- **Validation Commands & Results:** ต้องแนบ output ของ Compose validation, container
  health, Prometheus targets และ smoke test จาก UAT host ใน change record
- **Remaining TBDs & Residual Risks:** DNS/IP, firewall CIDRs, TLS certificates,
  backup target, retention และ business-approved RPO/RTO
- **Human Approval Required:** Platform/DevOps, Security/Network, DBA และ Data Owner
  ต้องอนุมัติก่อน UAT sign-off หรือ production promotion
