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

หากองค์กรบังคับใช้ approved private registry ให้ mirror images ที่ผ่านการ scan แล้ว
และกำหนด `MINIO_IMAGE`/`MINIO_MC_IMAGE` เป็น approved registry references แทน ห้ามปิด TLS
verification เพื่อแก้ปัญหาการ pull image

ใช้ approved release tag หรือ commit SHA ไม่ควร deploy จาก `main` โดยตรงหากยังไม่มี
CI และ human approval gate

### Build custom UAT images ก่อนเข้า Portainer

ไฟล์ Compose ที่ใช้ deploy ผ่าน Portainer ไม่มี `build:` เพื่อหลีกเลี่ยงการส่ง BuildKit/gRPC
ผ่าน Portainer Agent ให้ build บน Docker endpoint host โดยตรง หรือ build ใน CI แล้ว push
เข้า GHCR ก่อน deploy ห้ามเลือก `compose/docker-compose.uat-build.yml` เป็น Stack compose path

สำหรับ UAT host ที่ยังไม่ใช้ GHCR ให้ checkout approved reference บน **เครื่อง Docker endpoint
เดียวกับที่ Portainer environment ชี้อยู่** แล้ว build local images:

```bash
git fetch --tags
git checkout <APPROVED_RELEASE_TAG_OR_SHA>

sudo docker buildx inspect --bootstrap
sudo docker compose --env-file .env.example \
  -f compose/docker-compose.uat-build.yml build --pull

sudo docker image inspect \
  lakehouse/clickhouse-uat:26.8 \
  lakehouse/dbt-runner-uat:1.8.6 \
  lakehouse/serving-api-uat:1.0.0 \
  lakehouse/source-mssql-init:2022-CU16 \
  lakehouse/source-mongodb:8.0.4 \
  lakehouse/prometheus-uat:2.54.0 \
  lakehouse/grafana-uat:11.1.4 \
  lakehouse/loki-uat:3.1.1 >/dev/null
```

> [!IMPORTANT]
> คำสั่ง `docker image inspect` ด้านบนเป็น mandatory deployment gate ต้องจบด้วย exit code
> `0` บน Docker endpoint host ก่อนกด Deploy Stack ใดใน Portainer หากพบ
> `pull access denied for lakehouse/<image>` แสดงว่ายังข้ามขั้นตอน build/publish image
> การรัน `docker login` อย่างเดียวไม่สามารถแก้ได้ เพราะชื่อ `lakehouse/*` เป็น local tags
> และไม่มี repository บน public registry

Deployment Compose กำหนด `pull_policy: missing`: ถ้ามี local image อยู่แล้วจะใช้งานทันที
แต่ถ้าไม่มีจะพยายาม pull จาก registry ดังนั้นต้อง build local images ให้ครบ หรือกำหนด
`*_UAT_IMAGE` เป็น GHCR reference ที่ใช้ immutable tag/digest ก่อน deploy

ถ้าจะ deploy เฉพาะ Observability สามารถ build เฉพาะสาม images ได้:

```bash
sudo docker compose --env-file .env.example \
  -f compose/docker-compose.uat-build.yml build --pull \
  prometheus-uat grafana-uat loki-uat
```

แนวทางที่เลือกสำหรับ UAT นี้คือให้ GitHub Actions build และ push images ด้วย immutable
release tag เข้า GHCR จากนั้นเพิ่ม `ghcr.io` ใน **Portainer > Registries** และกำหนดตัวแปร
`*_UAT_IMAGE` เป็น GHCR reference ห้ามเก็บ GitHub PAT ใน Git ดูขั้นตอนที่
[Runbook 06: ใช้ GitHub และ GHCR กับ Portainer UAT](06_github_ghcr_uat.md)

หากองค์กรกลับมาใช้ Harbor ให้ดู
[Runbook 05: Harbor Registry สำหรับ UAT และ Portainer](05_harbor_uat_registry.md)

สำหรับ remote Docker environment ห้ามใส่ `build:` กลับเข้า Portainer deployment Compose
เพราะ Portainer 2.29.2 ขึ้นไปยังไม่รองรับ Compose build บน remote environment อย่างเสถียร
Git repository เป็น source ของ Compose/config และ CI เป็นผู้สร้าง images ตาม flow:

```text
GitHub tag -> GitHub Actions -> GHCR -> Portainer Git Stack -> UAT Docker endpoint
```

ก่อนสร้าง Stack จาก Git ให้เพิ่ม GHCR ที่ **Portainer > Registries** ด้วย GitHub username และ
read-only PAT แล้วทดสอบว่า endpoint pull approved release images ได้ครบ หาก GHCR ยังไม่มี
images ให้ใช้ local-build workflow ด้านบนชั่วคราว ห้ามคาดว่า Git PAT จะ build image ให้อัตโนมัติ

### สร้าง shared external networks ก่อนทุก Stack

รันบน **Docker endpoint host เดียวกับที่ Portainer environment ชี้อยู่** เพียงครั้งเดียว
ก่อน deploy Core, Data Sources, Streaming หรือ Observability:

```bash
sudo docker network inspect lakehouse-uat-integration >/dev/null 2>&1 || \
  sudo docker network create --driver bridge lakehouse-uat-integration

sudo docker network inspect lakehouse-uat-observability >/dev/null 2>&1 || \
  sudo docker network create --driver bridge lakehouse-uat-observability

sudo docker network inspect lakehouse-uat-integration >/dev/null
sudo docker network inspect lakehouse-uat-observability >/dev/null
```

ใน Portainer สามารถตรวจได้ที่ **Environment > Networks** ชื่อ network ต้องตรงทุกตัวอักษร
กับ environment variables และต้องอยู่บน endpoint เดียวกัน การสร้าง network บน Portainer
Server คนละเครื่องจะไม่ทำให้ network ปรากฏบน UAT endpoint

Network ที่คาดว่าจะเห็นหลัง deploy ครบทุก Stack มีดังนี้:

| Network | Ownership | หน้าที่ |
|---|---|---|
| `lakehouse-uat-integration` | External/shared | Core, Data Sources และ Streaming สื่อสารกัน |
| `lakehouse-uat-observability` | External/shared | Prometheus เข้าถึง metrics ของ Core |
| `lakehouse-uat-core_data_storage` | Core Stack/private | ClickHouse ติดต่อ MinIO ภายใน Core |

`lakehouse-uat-core_data_storage` ไม่ใช่ network ซ้ำ แต่เป็น private storage boundary
ส่วน `lakehouse-uat-core_management` และ `lakehouse-uat-observability_management`
ไม่จำเป็นใน UAT Compose รุ่นปัจจุบันและถูกนำออกแล้ว

หากพบ `network ... declared as external, but could not be found` ให้สร้าง network ที่ขาด
บน endpoint นี้ก่อนแล้วกด Deploy/Update Stack อีกครั้ง ไม่ต้องแก้ `external: true` เป็น false
เพราะ network ทั้งสองเป็นขอบเขตร่วมระหว่างหลาย stacks

หากเคย deploy release เก่าที่สร้าง `*_management` ให้ Update Core และ Observability Stack
เป็น release ปัจจุบันก่อน แล้วตรวจว่าไม่มี container เกาะ network เดิม:

```bash
sudo docker network inspect lakehouse-uat-core_management \
  --format '{{len .Containers}}' 2>/dev/null || true
sudo docker network inspect lakehouse-uat-observability_management \
  --format '{{len .Containers}}' 2>/dev/null || true
```

ลบเฉพาะ network ที่แสดง `0` เท่านั้น หาก Portainer/Compose ยังไม่ได้ลบให้อัตโนมัติ:

```bash
sudo docker network rm lakehouse-uat-core_management
sudo docker network rm lakehouse-uat-observability_management
```

ห้ามลบ `lakehouse-uat-integration`, `lakehouse-uat-observability` หรือ
`lakehouse-uat-core_data_storage` และห้ามใช้ `docker network prune` บน UAT host

## 6. Deploy Stack 1: UAT Core

ใน Portainer ไปที่ **Environments > Local > Stacks > Add stack > Repository**:

```text
Name: lakehouse-uat-core
Repository URL: https://github.com/kingpac-dev/Enterprise-Data-Lakehouse-Platform.git
Authentication: enabled
Username: <GITHUB_USERNAME_THAT_OWNS_PAT>
Personal Access Token: <GITHUB_PAT_FROM_SECRET_MANAGER>
Repository reference: refs/tags/<APPROVED_RELEASE_TAG>
Compose path: compose/docker-compose.dev.yml
```

ใช้ PAT เดียวกับ GHCR ได้เมื่อเป็น Personal Access Token (classic) ที่มี `read:packages`
และมีสิทธิ์อ่าน repository; หาก repository เป็น private ต้องมี `repo` ด้วย ห้ามใส่ PAT
ใน Environment variables ของ Stack หรือ commit ลง Git

เพิ่ม Environment variables ด้านล่างหลังจาก workflow publish release `uat-v1.0.6`
สำเร็จครบทุก image แล้ว:

```dotenv
ENVIRONMENT=uat
INTEGRATION_NETWORK=lakehouse-uat-integration
OBSERVABILITY_NETWORK=lakehouse-uat-observability
CLICKHOUSE_PORT_HTTP=18123
CLICKHOUSE_PORT_NATIVE=19000
CLICKHOUSE_PORT_PROMETHEUS=19363
CLICKHOUSE_UAT_IMAGE=ghcr.io/kingpac-dev/clickhouse-uat:uat-v1.0.6
DBT_RUNNER_UAT_IMAGE=ghcr.io/kingpac-dev/dbt-runner-uat:uat-v1.0.6
CLICKHOUSE_ADMIN_USER=admin
CLICKHOUSE_ADMIN_PASSWORD=<STRONG_SECRET>
CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1
CLICKHOUSE_SKIP_USER_SETUP=1
CLICKHOUSE_ALWAYS_RUN_INITDB_SCRIPTS=
CLICKHOUSE_ETL_PASSWORD=<STRONG_SECRET>
CLICKHOUSE_BI_PASSWORD=<STRONG_SECRET>
CLICKHOUSE_API_PASSWORD=<STRONG_SECRET>
CLICKHOUSE_MONITORING_PASSWORD=<STRONG_SECRET>
S3_PORT=19090
MINIO_CONSOLE_PORT=19091
MINIO_IMAGE=quay.io/minio/minio:RELEASE.2024-08-17T01-24-54Z@sha256:6f23072e3e222e64fe6f86b31a7f7aca971e5129e55cbccef649b109b8e651a1
MINIO_MC_IMAGE=quay.io/minio/mc:RELEASE.2024-08-13T05-33-17Z@sha256:07c08763869bb18306d6f33a7e887c42211b1585a63c9098c9cf28b1b45b19aa
S3_BUCKET_LAKE=enterprise-data-lake-uat
S3_ACCESS_KEY=<MINIO_ROOT_USERNAME>
S3_SECRET_KEY=<STRONG_UNIQUE_MINIO_ROOT_SECRET>
S3_REGION=us-east-1
CLICKHOUSE_S3_ENDPOINT=http://minio:9000/enterprise-data-lake-uat/clickhouse_data/
CLICKHOUSE_CPU_LIMIT=4
CLICKHOUSE_MEMORY_LIMIT=8G
CLICKHOUSE_MEMORY_RESERVATION=4G
SERVING_API_PORT=18000
SERVING_API_UAT_IMAGE=ghcr.io/kingpac-dev/serving-api-uat:uat-v1.0.6
```

แทนค่าทุก placeholder ด้วยค่าจริงก่อน Deploy
โดยค่าปกติของ `CLICKHOUSE_ALWAYS_RUN_INITDB_SCRIPTS` ต้องเว้นว่าง ใส่ `1` ชั่วคราวเฉพาะ
recovery bootstrap ตามหัวข้อแก้ไข ClickHouse ด้านล่างเท่านั้น
ห้ามคัดลอกเครื่องหมาย `<` และ `>` ไปใช้เป็นส่วนหนึ่งของรหัสผ่าน

### Credential ของ MinIO Console

UAT Compose รุ่นปัจจุบัน map ค่า `S3_ACCESS_KEY` ไปเป็น `MINIO_ROOT_USER` และ
`S3_SECRET_KEY` ไปเป็น `MINIO_ROOT_PASSWORD` ดังนั้น credential ของหน้า MinIO Console คือ:

| หน้าเว็บ | URL | Username | Password |
|---|---|---|---|
| MinIO Console | `http://<UAT_HOST>:19091` | ค่า `S3_ACCESS_KEY` ของ Core Stack | ค่า `S3_SECRET_KEY` ของ Core Stack |
| Grafana | `http://<UAT_HOST>:13000` | ค่า `GRAFANA_ADMIN_USER` ของ Observability Stack | ค่า `GRAFANA_ADMIN_PASSWORD` ของ Observability Stack |
| Portainer | `https://<UAT_HOST>:9443` | Portainer account | Portainer password |

ห้ามนำ `GRAFANA_ADMIN_USER`/`GRAFANA_ADMIN_PASSWORD` ไป login MinIO แม้ username
จะเป็น `admin` เหมือนกัน เพราะเป็นคนละ container และคนละ credential store

หาก MinIO แสดง `Invalid Login`:

1. ไปที่ **Stacks > lakehouse-uat-core > Editor/Environment variables** แล้วตรวจ
   `S3_ACCESS_KEY` และ rotate `S3_SECRET_KEY` เป็นค่าที่ไม่ซ้ำกับ Grafana/Portainer
2. กด **Pull and redeploy** เพื่อ recreate Core containers โดยไม่เลือก remove volumes
3. ตรวจ username ที่ container ได้รับจริง โดยคำสั่งนี้ไม่แสดง password:

```bash
sudo docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' \
  lakehouse-minio | sed -n 's/^MINIO_ROOT_USER=//p'

sudo docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' \
  lakehouse-minio | grep -q '^MINIO_ROOT_PASSWORD=..*$' && \
  echo 'MINIO_ROOT_PASSWORD is set'

sudo docker inspect --format '{{.Created}}' lakehouse-minio
sudo docker logs --tail 100 lakehouse-minio
curl -fsS http://127.0.0.1:19090/minio/health/ready
```

4. เปิดหน้าต่าง browser แบบ private/incognito แล้ว login ด้วยค่าจาก Core Stack

การเปลี่ยน `S3_ACCESS_KEY`/`S3_SECRET_KEY` จะเปลี่ยน credential ที่ ClickHouse ใช้เข้าถึง
MinIO ด้วย จึงต้อง redeploy Core Stack ทั้งชุดและตรวจ ClickHouse health หลังการ rotate

### ClickHouse Code 1000: ห้ามใช้ inline fallback ร่วมกับ `from_env`

หาก log แสดงข้อความลักษณะนี้:

```text
Element <shard> has value and does not have 'replace' attribute,
can't process from_env substitution
```

แสดงว่า `clickhouse-uat` image มี XML element ที่กำหนด `from_env` พร้อม inline fallback text
ซึ่งอาจล้มเหลวระหว่างการ merge/preprocess config fragment การแก้เฉพาะ Environment variables
ใน Portainer ไม่เพียงพอ เพราะ XML ถูก bake อยู่ใน image

Platform นี้จึงไม่ใช้ inline fallback ใน ClickHouse XML อีก รูปแบบที่กำหนดคือ
`<endpoint from_env="CLICKHOUSE_S3_ENDPOINT"/>` และส่งค่าบังคับผ่าน Compose/Portainer
Environment variables เท่านั้น วิธีนี้ใช้กับ password, S3, cluster macro และ Keeper server ID
ทั้งหมด ส่วน UAT Dockerfile
ไม่ copy Production HA cluster/Keeper config เข้า Single Node อีก ขั้นตอนนำขึ้นใช้:

ถ้า error ระบุ `Failed to preprocess config '/etc/clickhouse-server/users.xml'` และ
`Element <password> has value` แสดงว่า Docker entrypoint กับ `users.d/users.xml` กำลังสร้าง
ผู้ใช้ `admin` ซ้ำกัน Environment จึงต้องมี `CLICKHOUSE_SKIP_USER_SETUP=1` เสมอ โดย custom
`users.xml` จะเป็นแหล่งกำหนด admin/service users เพียงแหล่งเดียวและลบ image user `default`
อย่างชัดเจน ห้ามเปลี่ยนค่านี้เป็น `0` ใน UAT/PROD Compose ปัจจุบัน

ถ้า GitHub Actions แสดง `ClickHouse did not become ready` โดย log จบใกล้ข้อความ
`Disk s3_cold started up` และไม่มี fatal exception แปลว่าเป็น failure ของ runtime smoke test
ไม่ใช่ XML preprocessing รอบเดิม รุ่น `uat-v1.0.5` ใช้ S3 endpoint แบบ loopback
`127.0.0.1:19090` ภายใน ClickHouse container ทั้งที่ไม่มี MinIO อยู่ใน container นั้น จึงห้าม
นำ tag ดังกล่าวไป Deploy การแก้ไขตั้งแต่ candidate `uat-v1.0.6` เป็นต้นไปจะสร้าง MinIO ชั่วคราว,
สร้าง bucket `validation` และเชื่อม ClickHouse/MinIO ผ่าน isolated Docker network ก่อนรัน
`SELECT 1`; workflow จะลบ container/network ชั่วคราวเมื่อ job จบ

1. Commit/push การแก้ไขผ่าน review และ merge เข้า branch ที่อนุมัติแล้ว
2. วิธีที่แนะนำคือสร้าง Git tag ใหม่จาก commit ที่อนุมัติแล้ว เช่น `uat-v1.0.6` แล้ว push tag
   เพื่อให้ workflow checkout source ตรงกับ release เสมอ:

   ```bash
   git checkout main
   git pull --ff-only
   git tag -a uat-v1.0.6 -m "UAT release uat-v1.0.6"
   git push origin uat-v1.0.6
   ```

   หากใช้ **Run workflow** แบบ manual ต้องเลือก **Use workflow from** เป็น default branch
   ที่ merge การแก้ไขนี้แล้วก่อนกรอก `release_tag` ใหม่ ตัว workflow จะปฏิเสธ branch อื่น
   ห้ามรันจาก `main` รุ่นเก่า และห้ามใช้ `uat-v1.0.0` ถึง `uat-v1.0.5` ซ้ำ
3. รอให้ GitHub Actions **Publish UAT Images to GHCR** ผ่านครบทุก image โดย ClickHouse
   smoke test ต้องสตาร์ต ClickHouse จริงและ `SELECT 1` ด้วยผู้ใช้ `admin` ผ่าน
4. เปลี่ยน Core Stack variable:

```dotenv
CLICKHOUSE_UAT_IMAGE=ghcr.io/kingpac-dev/clickhouse-uat:uat-v1.0.6
```

เฉพาะกรณีกู้คืน volume ที่เริ่ม bootstrap ค้างจาก image รุ่นก่อน ให้เพิ่มชั่วคราว:

```dotenv
CLICKHOUSE_ALWAYS_RUN_INITDB_SCRIPTS=1
```

SQL ชุด `01`-`05` ถูกออกแบบให้รันซ้ำได้ แต่ห้ามใช้ค่านี้กับ Production โดยไม่มี human approval

5. กด **Pull and redeploy** โดยไม่ลบ volumes แล้วตรวจ:

```bash
sudo docker inspect --format '{{.Config.Image}} restart={{.RestartCount}} status={{.State.Status}}' \
  lakehouse-clickhouse-dev
sudo docker logs --tail 200 lakehouse-clickhouse-dev
curl -fsS http://127.0.0.1:18123/ping
```

ผลที่ต้องการคือ image tag ใหม่, restart count ไม่เพิ่มต่อเนื่อง, ไม่มี Code 1000 และ `/ping`
ตอบ `Ok.` ห้าม reuse/overwrite tag เดิม เพราะ Docker endpoint อาจใช้ cached image เก่า
เมื่อยืนยันว่า database `raw`, `core`, `mart`, `serving` และ RBAC ถูกสร้างครบแล้ว ให้ลบค่า
`CLICKHOUSE_ALWAYS_RUN_INITDB_SCRIPTS` หรือกำหนดเป็นค่าว่าง จากนั้น Pull and redeploy อีกครั้ง

หาก container ค้างที่ `Processing configuration file` และ Portainer แสดง `unhealthy` ให้ตรวจ
`docker logs` ก่อนลบ volume เสมอ ตั้งแต่ `uat-v1.0.6` เป็นต้นไป startup/fatal log จะถูกส่งออก
console ของ container และ external S3/Iceberg template จะไม่ถูกรันระหว่าง bootstrap อัตโนมัติ
พอร์ต `19000` เป็น ClickHouse native protocol จึงเปิดด้วย browser ไม่ได้ ส่วน Prometheus ต้องตรวจที่
`http://<UAT_HOST>:19363/metrics` ไม่ใช่ path `/`

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

ตรวจ shared external networks ที่เตรียมไว้ก่อน deploy:

```bash
sudo docker network inspect lakehouse-uat-integration >/dev/null
sudo docker network inspect lakehouse-uat-observability >/dev/null
```

ห้าม deploy stack ใดจนกว่าสอง networks นี้จะมีอยู่จริง

## 7. Deploy Stack 2: UAT Data Sources

```text
Name: lakehouse-uat-datasources
Repository reference: ใช้ tag/SHA เดียวกับ Core
Compose path: compose/docker-compose.datasources.yml
```

Environment variables:

```dotenv
INTEGRATION_NETWORK=lakehouse-uat-integration
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
SOURCE_MSSQL_INIT_IMAGE=ghcr.io/kingpac-dev/source-mssql-init:uat-v1.0.6
SOURCE_MONGODB_PORT=17017
SOURCE_MONGODB_DB=source_uat
SOURCE_MONGODB_ROOT_USER=mongo_admin
SOURCE_MONGODB_ROOT_PASSWORD=<STRONG_ROOT_SECRET>
SOURCE_MONGODB_USER=source_app
SOURCE_MONGODB_PASSWORD=<STRONG_APP_SECRET>
SOURCE_MONGODB_UAT_IMAGE=ghcr.io/kingpac-dev/source-mongodb:uat-v1.0.6
```

กด **Deploy the stack** แล้วตรวจ PostgreSQL, MySQL, SQL Server และ MongoDB เป็น
`healthy`; `source-mssql-init` ต้องจบด้วย exit code `0`

ตรวจ image mapping หลัง deploy ทุกครั้ง:

```bash
sudo docker inspect --format '{{.Name}} -> {{.Config.Image}}' \
  lakehouse-source-mssql-init lakehouse-source-mongodb
```

ค่าที่ถูกต้องสำหรับตัวอย่าง release `uat-v1.0.6` คือ:

```text
lakehouse-source-mssql-init -> ghcr.io/kingpac-dev/source-mssql-init:uat-v1.0.6
lakehouse-source-mongodb -> ghcr.io/kingpac-dev/source-mongodb:uat-v1.0.6
```

หากสอง container นี้แสดง `serving-api-uat` หรือ log มี `uvicorn`/
`ModuleNotFoundError: No module named 'data_quality'` แสดงว่ากำหนด Portainer variables
ผิด image ให้แก้เป็น:

```dotenv
SOURCE_MSSQL_INIT_IMAGE=ghcr.io/kingpac-dev/source-mssql-init:uat-v1.0.6
SOURCE_MONGODB_UAT_IMAGE=ghcr.io/kingpac-dev/source-mongodb:uat-v1.0.6
```

แล้วกด **Pull and redeploy** Data Sources Stack โดยไม่ลบ database volumes

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
PROMETHEUS_UAT_IMAGE=ghcr.io/kingpac-dev/prometheus-uat:uat-v1.0.6
GRAFANA_UAT_IMAGE=ghcr.io/kingpac-dev/grafana-uat:uat-v1.0.6
LOKI_UAT_IMAGE=ghcr.io/kingpac-dev/loki-uat:uat-v1.0.6
PROMETHEUS_PORT=19093
GRAFANA_PORT=13000
LOKI_PORT=13100
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=<STRONG_SECRET>
```

Compose ชุด UAT จะ pull หรือใช้ images ที่ build ไว้บน endpoint host แล้ว จึงไม่ส่ง build
ผ่าน Portainer Agent ไม่ต้องเพิ่มไฟล์ใน **Additional paths** และไม่ใช้ relative bind mount
สำหรับ config เมื่อ deploy ผ่าน Portainer Git Stack

หากพบ `pull access denied for lakehouse/prometheus-uat` หรือข้อความเดียวกันสำหรับ Grafana/Loki
หมายถึง custom images ยังไม่มีบน Docker endpoint และไม่มี repository ชื่อนี้ใน public registry
ให้ SSH เข้า endpoint host แล้ว checkout Git reference เดียวกับ Stack จากนั้นรัน:

```bash
sudo docker compose --env-file .env.example \
  -f compose/docker-compose.uat-build.yml build --pull \
  prometheus-uat grafana-uat loki-uat

sudo docker image inspect \
  lakehouse/prometheus-uat:2.54.0 \
  lakehouse/grafana-uat:11.1.4 \
  lakehouse/loki-uat:3.1.1 >/dev/null
```

เมื่อคำสั่ง `image inspect` สำเร็จจึงกด Deploy อีกครั้ง หากใช้ GHCR ให้เปลี่ยนตัวแปร
สามรายการเป็น GHCR image references และตั้ง GitHub credential ใน Portainer Registries

Deploy แล้วตรวจ Prometheus, Grafana และ Loki เป็น `running` จากนั้นเปิด Prometheus
**Status > Targets** และยืนยันว่า `clickhouse:9363` กับ `minio:9000` เป็น `UP`

Grafana เปิดที่ `http://<UAT_HOST>:13000`; port `19091` เป็น MinIO Console และไม่รับ
`GRAFANA_ADMIN_USER`/`GRAFANA_ADMIN_PASSWORD`

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
images จาก GHCR ไม่แนะนำให้ตั้ง `DOCKER_BUILDKIT=0` เป็นวิธีถาวร เพราะเป็นเพียง workaround
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

หยุดย้อนลำดับ: Observability > Streaming > Data Sources > Core ห้ามลบ shared external
networks ขณะที่ยังมี stack ใดเชื่อมต่ออยู่ และห้าม remove volumes หากไม่มี written approval
พร้อม verified backup/restore evidence

## Handoff Contract

- **Scope & Sources Inspected:** UAT Core, Data Sources, Streaming, Observability,
  environment template, GitHub/GHCR image flow, monitoring configuration และ governance policy
- **Assumptions & Decisions:** Ubuntu 24 LTS, Docker Compose V2, Git-backed Stacks,
  UAT Single Node, shared integration/observability networks, private Core storage network
  และ masked/synthetic data
- **Security & Operational Impact:** Secrets และ GitHub PAT อยู่ใน Portainer/secret manager;
  MinIO, Grafana และ Portainer ใช้รหัสผ่านไม่ซ้ำกัน; GHCR ใช้ pull-only permission;
  external ports จำกัดด้วย firewall/VPN/TLS; application accounts ใช้ least privilege
- **Validation Commands & Results:** ต้องแนบ output ของ Compose validation, container
  image mapping, health, Prometheus targets และ smoke test จาก UAT host ใน change record
- **Remaining TBDs & Residual Risks:** การยืนยัน/ลบ stale `*_management` networks บน UAT,
  GitHub service account/PAT expiration, GHCR package visibility/scan gate, DNS/IP,
  firewall CIDRs, TLS certificates, backup target, retention และ business-approved RPO/RTO
- **Human Approval Required:** Platform/DevOps, Security/Network, DBA และ Data Owner
  ต้องอนุมัติก่อน UAT sign-off หรือ production promotion
