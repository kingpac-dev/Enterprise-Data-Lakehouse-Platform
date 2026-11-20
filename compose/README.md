# Compose stacks — แยกตาม Environment และหน้าที่

ไดเรกทอรีนี้แสดง **Compose entrypoints** สำหรับแต่ละ Portainer stack แบบ Git-backed; entrypoint ใช้ `include` อ้างไฟล์ definition เดิมเพียงชุดเดียว จึงไม่ต้องสำเนา definitions และไม่ต้องย้ายไฟล์ที่ Portainer/Git/CI อาจอ้างอยู่. ไฟล์เดิม `compose/docker-compose.*.yml` ยังคงเป็น canonical definitions; แก้ definitions ที่ไฟล์เดิม ไม่แก้ทั้งสองที่

| Environment | Function / Portainer stack | Grouped Compose path | Definition เดิม | หมายเหตุ |
|---|---|---|---|---|
| UAT | Core / `lakehouse-uat-core` | [core](uat/core/compose.yml) | [dev](docker-compose.dev.yml) | ClickHouse, MinIO; RustFS/dbt/API เป็น profiles |
| UAT | Data Sources / `lakehouse-uat-datasources` | [datasources](uat/datasources/compose.yml) | [datasources](docker-compose.datasources.yml) | source DBs; synthetic/masked data |
| UAT | Streaming / `lakehouse-uat-streaming` | [streaming](uat/streaming/compose.yml) | [streaming](docker-compose.streaming.yml) | Redpanda + Console |
| UAT | Observability / `lakehouse-uat-observability` | [observability](uat/observability/compose.yml) | [observability](docker-compose.observability.yml) | Prometheus, Grafana, Loki |
| UAT | Insight / `kingpac-insight-uat` | [insight](uat/insight/compose.yml) | [insight-uat](docker-compose.insight-uat.yml) | Superset + metadata PostgreSQL + Redis |
| UAT | Build images only | [build](uat/build/compose.yml) | [uat-build](docker-compose.uat-build.yml) | ไม่ใช่ runtime stack |
| PROD candidate | Core single node | [core](prod/core/compose.single-node.yml) | [prod-single](docker-compose.prod-single.yml) | single host จัดเป็น DEV/UAT ตาม AGENTS.md ไม่ใช่ HA |
| PROD candidate | Data Sources | [datasources](prod/datasources/compose.yml) | [prod-datasources](docker-compose.prod-datasources.yml) | optional `insight-redis` profile ไม่ใช่ HA |
| PROD candidate | Storage | [storage](prod/storage/compose.yml) | [prod-minio](docker-compose.prod-minio.yml) | single-host MinIO ไม่ใช่ independent backup |
| PROD candidate | Insight | [insight](prod/insight/compose.yml) | [insight-prod](docker-compose.insight-prod.yml) | web; external PostgreSQL/Redis/Keycloak และ maintenance profile |
| PROD HA candidate | Multi-host node 1 | [node1](prod/multi-host/node1.yml) | [prod-node1](docker-compose.prod-node1.yml) | target HA; readiness gates ยังไม่ผ่าน |
| PROD HA candidate | Multi-host node 2 | [node2](prod/multi-host/node2.yml) | [prod-node2](docker-compose.prod-node2.yml) | target HA; readiness gates ยังไม่ผ่าน |
| PROD HA candidate | Keeper node 3 | [keeper3](prod/multi-host/keeper3.yml) | [prod-keeper3](docker-compose.prod-keeper3.yml) | target HA; readiness gates ยังไม่ผ่าน |

**ยังไม่มี approved PROD Streaming หรือ Observability Compose**; UAT definitions ไม่ได้กลายเป็น production-ready เมื่อเปลี่ยนชื่อ. [Grafana Insight UAT overlay](docker-compose.insight-grafana-uat.yml) เป็น optional override ของ observability stack ไม่ใช่ stack อีกตัว. [stack-groups.single-node.json](stack-groups.single-node.json) เก็บทั้ง `compose` เดิมและ `grouped_compose` เพื่อ mapping; ชื่อที่แสดงเป็นชื่อในภาพ/ชื่อที่เสนอ ไม่ได้ยืนยัน deployment ปัจจุบันจาก API

## ข้อกำหนด Portainer และการใช้งาน

1. Docker Compose CLI ต้องรองรับ `include` (ใช้ 2.20.3 ขึ้นไปตาม [Docker documentation](https://docs.docker.com/compose/how-tos/multiple-compose-files/include/)). ตรวจ Portainer version/stack deployment engine จริงว่ารองรับ Compose include และ Git clone มีทั้ง repo พร้อม relative paths ก่อนใช้ grouped path; ไม่ใช่ทุก Portainer/version/deployment mode รองรับตามกัน และยังไม่ได้ทดสอบกับ live Portainer. ไฟล์ต้นฉบับยังใช้ได้หาก environment ไม่รองรับ
2. Git-backed Stack ต้องให้ included path `../../docker-compose...` resolve ไปที่ไฟล์ใน Git checkout เดียวกัน. ไม่ควรนำ entrypoint เพียงไฟล์เดียวไปวางใน Web Editor เพราะไฟล์ที่ include อาจไม่มีอยู่บน host. ค่า `Stack.env` / secrets คงแยกจาก Git ตาม runbook และต้องเตรียม external networks ก่อน deploy
3. Screenshot แสดง UAT 4 stack entries; ไม่แสดง effective project name, Git ref/path, health หรือ volume identities. **อย่าเปลี่ยน live path/stack name ทันที**: inventory actual Portainer stack name, Compose project (`com.docker.compose.project`), physical volume/network/container names, active profiles, env และ version แล้วทำ staged change/review. ห้ามสร้าง stack ใหม่ซ้ำที่ชี้ volume/container เดิมโดยไม่มี migration plan
4. ใน Portainer ชื่อ stack/project ที่มีผลอาจ override top-level `name:` ของไฟล์. ห้ามเปลี่ยน effective project name โดยไม่ได้ตรวจ physical volumes/network names; การเปลี่ยน project อาจสร้าง volumes ใหม่หรือชน fixed `container_name`. โดยเฉพาะ streaming definition เดิมไม่มี top-level `name:` ส่วน grouped file กำหนด `lakehouse-uat-streaming`; CLI ที่ไม่ระบุ `-p` อาจได้ project/volume names ต่างกัน. ทดสอบด้วย project name จริงและ backup/restore ก่อนเสนอ migration. Network และ data ไม่ถูกย้ายโดยการเปลี่ยนชื่อไฟล์
5. UAT `INSIGHT_PORT` และ Redpanda Console default ชนกันที่ `18088`; ตรวจ ports จริงและกำหนด `INSIGHT_PORT=18089` สำหรับ UAT ใหม่หากว่าง. UAT กับ PROD ต้องใช้ Docker environments/hosts แยก; fixed container names, volumes, ports และ networks อาจชนกันหากรวม daemon. Production single-node เป็น candidate สำหรับ DEV/UAT เท่านั้น; อย่าเปิดรับ production traffic

### ตัวอย่างตรวจบนเครื่อง build/test

จาก repository root ใช้ env ที่เป็น synthetic เท่านั้น และกำหนด `-p` ให้ตรง effective project ที่ต้องการทดสอบ:

```bash
python scripts/check_single_node_stack_groups.py
python scripts/check_grouped_compose_equivalence.py
docker compose --env-file /path/to/nonsecret-test.env -p <existing-project-name> -f compose/uat/core/compose.yml config --quiet
```

สำหรับ optional Grafana overlay ให้ใช้ base `compose/uat/observability/compose.yml` ร่วมกับ `compose/docker-compose.insight-grafana-uat.yml` เป็น additional Compose file และ environment variables ตาม [BI UAT runbook](../runbooks/07_kingpac_insight_uat.md). ตรวจว่า Portainer รุ่นที่ใช้รองรับ additional files กับ Git stack ก่อนเปลี่ยนจริง; local Compose model ของ overlay ได้รับการเทียบกับ base path เดิมโดยใช้ dummy values แล้ว

Script เปรียบเทียบ Compose models ของ 13 pairs ภายใต้ **project name เดียวกันและ dummy variables**, รวมทุก profile และไม่เริ่ม containers. จะละ top-level `x-*` ซึ่งเป็น extension metadata; ไม่ยืนยันความเท่ากันของ CLI default project name, ไฟล์ `.env` จริง, Portainer UI, secrets, external networks หรือ live volumes. อย่า print `docker compose config` ที่รวม secrets จริง; ใช้ `--quiet`

## Impact / rollback / approval

- ไฟล์เดิม, Compose services, project/volume definitions และ Portainer deployment เดิมไม่เปลี่ยน; เพิ่ม grouped entrypoints เท่านั้น. ไม่มีการลบหรือสร้าง volume และยังไม่ได้ทดสอบ deploy จริง
- หลัง review หาก operator เปลี่ยน Git path ให้คง effective project name และ verify outputs, mounts, networks, health และ application behavior; rollback ใช้ Git revision และ Compose path เดิมภายใต้ project name เดิม. การ rollback path ไม่กู้ข้อมูลที่มีการย้ายหรือลบ; ต้องมี backup/restore ที่ทดสอบแล้วสำหรับ migration. ห้าม `down -v`
- ดู [Stack Groups runbook](../docs/STACK_GROUPS_SINGLE_NODE.md), [UAT runbook](../runbooks/01_portainer_git_stack_deployment.md), [production gate](../runbooks/04_portainer_prod_deployment.md) และ [Insight env templates](../deployment/kingpac-insight/README.md). Production promotion, destructive migration และ security exceptions ต้องผ่าน human approval ตาม [AGENTS.md](../AGENTS.md)
