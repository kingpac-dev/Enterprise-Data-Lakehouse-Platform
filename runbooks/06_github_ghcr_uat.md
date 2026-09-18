# Runbook 06: ใช้ GitHub และ GHCR กับ Portainer UAT

เอกสารนี้เป็นวิธีที่แนะนำเมื่อไม่ติดตั้ง Harbor โดยใช้ GitHub repository เป็นแหล่ง Compose/config
และ GitHub Container Registry (`ghcr.io`) เป็นแหล่ง custom images สำหรับ UAT

```text
Git tag / Manual approval -> GitHub Actions -> GHCR -> Portainer -> UAT Docker endpoint
```

> [!CAUTION]
> แนวทางนี้เป็น UAT Single Node เท่านั้น การเปลี่ยน Harbor เป็น GHCR สำหรับ Production
> เป็นข้อยกเว้นจาก platform baseline และต้องผ่าน Security/Platform/Change approval

## 1. Credential ที่ใช้กับ Portainer

ค่า **Username** ต้องเป็น GitHub username ของผู้ที่เป็นเจ้าของ token ไม่ใช่ชื่อ organization
เว้นแต่ชื่อทั้งสองตรงกัน ส่วน **Personal Access Token** ต้องเก็บใน Portainer/secret manager เท่านั้น
ห้ามใส่ใน Git, Compose, `.env` หรือเอกสาร

วิธีใช้ credential ชุดเดียวที่ง่ายที่สุด:

- Repository public และ GHCR private: Personal access token (classic) ที่มี `read:packages`
- Repository private และ GHCR private: Personal access token (classic) ที่มี `repo` และ `read:packages`
- หาก organization บังคับ SSO ต้อง authorize token ให้ organization `kingpac-dev`

ค่า `repo` เป็น scope กว้าง หากนโยบายองค์กรอนุญาต แนะนำแยก fine-grained read-only token
สำหรับ Git repository และ classic PAT ที่มีเพียง `read:packages` สำหรับ GHCR ตามหลัก least privilege

## 2. Publish UAT images ไป GHCR

Workflow `.github/workflows/publish-uat-images.yml` ใช้ `GITHUB_TOKEN` ที่ GitHub สร้างให้
จึงไม่ต้องเพิ่ม PAT สำหรับการ push image ใน repository secrets

1. Merge source และ workflow ผ่าน review ไปยัง default/approved branch
2. ไปที่ **GitHub > Actions > Publish UAT Images to GHCR**
3. วิธีที่แนะนำ: สร้าง Git tag ใหม่รูปแบบ `uat-v*` จาก commit ที่อนุมัติแล้วและ push tag
4. ทางเลือก: เลือก **Run workflow** จาก default branch เท่านั้น และระบุ image tag ใหม่
   เช่น `uat-v1.0.2` ห้าม reuse tag ที่มีอยู่ใน GHCR
5. รอให้ทั้ง 8 matrix jobs สำเร็จ และตรวจ package manifests/digests ใน GitHub Packages

Workflow จะตรวจว่า tag ยังไม่มีอยู่, build image candidate, ทำ smoke test แล้วจึง push เข้า GHCR
ถ้า ClickHouse XML ไม่ผ่าน ตัว image จะไม่ถูก publish รอบใหม่ ส่วน release ที่เคย publish ไม่ครบ
หรือ smoke test ไม่ผ่านต้องเปลี่ยนเป็น tag ใหม่ ห้ามเขียนทับ tag เดิม

Workflow จะ publish:

```text
ghcr.io/kingpac-dev/clickhouse-uat:<RELEASE_TAG>
ghcr.io/kingpac-dev/dbt-runner-uat:<RELEASE_TAG>
ghcr.io/kingpac-dev/serving-api-uat:<RELEASE_TAG>
ghcr.io/kingpac-dev/source-mssql-init:<RELEASE_TAG>
ghcr.io/kingpac-dev/source-mongodb:<RELEASE_TAG>
ghcr.io/kingpac-dev/prometheus-uat:<RELEASE_TAG>
ghcr.io/kingpac-dev/grafana-uat:<RELEASE_TAG>
ghcr.io/kingpac-dev/loki-uat:<RELEASE_TAG>
```

ห้ามใช้ `latest` และห้ามอ้าง tag ที่ workflow ยัง publish ไม่สำเร็จ

## 3. ตั้ง Git Repository Authentication ใน Portainer

เมื่อสร้างหรือแก้ Git-backed Stack:

```text
Repository URL: https://github.com/kingpac-dev/Enterprise-Data-Lakehouse-Platform.git
Authentication: enabled
Username: <GITHUB_USERNAME_THAT_OWNS_PAT>
Personal Access Token: <GITHUB_PAT_FROM_SECRET_MANAGER>
Repository reference: refs/tags/<APPROVED_RELEASE_TAG>
```

PAT ใช้แทน password และต้องมีสิทธิ์อ่าน repository ตามข้อ 1

## 4. เพิ่ม GHCR ใน Portainer

ไปที่ **Registries > Add registry > Custom registry**:

```text
Name: github-ghcr-kingpac
Registry URL: ghcr.io
Authentication: enabled
Username: <GITHUB_USERNAME_THAT_OWNS_PAT>
Password: <GITHUB_PAT_FROM_SECRET_MANAGER>
```

ใช้ PAT เดียวกับ Git repository ได้เมื่อได้รับอนุมัติและมี `read:packages` แต่ห้ามใช้ PAT
ที่มี `write:packages` หรือ `delete:packages` กับ Portainer เพราะ Portainer ต้องการ pull เท่านั้น

## 5. กำหนด image variables ของแต่ละ Stack

Core:

```dotenv
CLICKHOUSE_UAT_IMAGE=ghcr.io/kingpac-dev/clickhouse-uat:<NEW_RELEASE_TAG>
DBT_RUNNER_UAT_IMAGE=ghcr.io/kingpac-dev/dbt-runner-uat:<NEW_RELEASE_TAG>
SERVING_API_UAT_IMAGE=ghcr.io/kingpac-dev/serving-api-uat:<NEW_RELEASE_TAG>
```

Data Sources:

```dotenv
SOURCE_MSSQL_INIT_IMAGE=ghcr.io/kingpac-dev/source-mssql-init:<NEW_RELEASE_TAG>
SOURCE_MONGODB_UAT_IMAGE=ghcr.io/kingpac-dev/source-mongodb:<NEW_RELEASE_TAG>
```

Observability:

```dotenv
PROMETHEUS_UAT_IMAGE=ghcr.io/kingpac-dev/prometheus-uat:<NEW_RELEASE_TAG>
GRAFANA_UAT_IMAGE=ghcr.io/kingpac-dev/grafana-uat:<NEW_RELEASE_TAG>
LOKI_UAT_IMAGE=ghcr.io/kingpac-dev/loki-uat:<NEW_RELEASE_TAG>
```

ทุก Stack ของ release เดียวกันต้องใช้ tag เดียวกัน จากนั้นกด **Pull and redeploy** ตามลำดับ
Core > Data Sources > Streaming > Observability

## 6. Acceptance checks

ทดสอบจาก UAT Docker endpoint ก่อน deploy:

```bash
read -rsp "GHCR PAT: " GHCR_READ_PAT
echo
echo "${GHCR_READ_PAT}" |
  sudo docker login ghcr.io -u <GITHUB_USERNAME_THAT_OWNS_PAT> --password-stdin
unset GHCR_READ_PAT

sudo docker pull ghcr.io/kingpac-dev/clickhouse-uat:<NEW_RELEASE_TAG>
sudo docker image inspect ghcr.io/kingpac-dev/clickhouse-uat:<NEW_RELEASE_TAG>
```

ตรวจทุก package ใน GitHub ว่า repository access/visibility อนุญาตให้ PAT อ่านได้ หากพบ
`denied` หรือ `manifest unknown` ให้ตรวจ package permission และ tag ก่อน ห้ามเพิ่มสิทธิ์ write
ให้ Portainer เพื่อแก้ปัญหา pull

## 7. Security และข้อจำกัด

- Rotate/revoke PAT ตามนโยบาย และกำหนด expiration
- ใช้ machine/service account แทน personal account เมื่อองค์กรรองรับ
- ปิด GitOps automatic updates จนกว่าจะมี approval gate
- GHCR ไม่ทดแทน Trivy approval, SBOM, retention และ promotion controls โดยอัตโนมัติ
- Production ต้องใช้ digest และผ่าน vulnerability scan/promotion ตามนโยบายองค์กร

## 8. เอกสารอ้างอิง

- [GitHub: Working with the Container registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [GitHub: Publishing Docker images](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images)

## Handoff Contract

- **Scope & Sources Inspected:** GitHub repository authentication, GitHub Actions,
  GHCR authentication, Portainer custom registry และ UAT image variables
- **Assumptions & Decisions:** ใช้ GitHub + GHCR แทน Harbor เฉพาะ UAT และ publish ด้วย
  repository `GITHUB_TOKEN`
- **Security & Operational Impact:** Portainer ใช้ read-only PAT; token ไม่อยู่ใน Git;
  package visibility/access ต้องกำหนดที่ GitHub
- **Validation Commands & Results:** ต้องเก็บ workflow result, GHCR manifest/digest,
  Docker pull และ Stack health outputs เป็น UAT evidence
- **Remaining TBDs & Residual Risks:** PAT owner/service account, expiration, package visibility,
  vulnerability scan gate, retention และ immutable-tag policy
- **Human Approval Required:** Repository Admin, Security และ Platform/DevOps ต้องอนุมัติ
  workflow permissions, PAT scopes และ UAT release ก่อน deploy
