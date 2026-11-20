# KingPac Insight Stack.env — UAT และ Production candidate

| Environment | ไฟล์ใช้งานใน workspace | Template สำหรับ Git | Compose |
|---|---|---|---|
| UAT | `uat/Stack.env` | [Stack.env.example](uat/Stack.env.example) | [insight-uat](../../compose/docker-compose.insight-uat.yml) |
| PROD candidate | `prod/Stack.env` | [Stack.env.example](prod/Stack.env.example) | [insight-prod](../../compose/docker-compose.insight-prod.yml) |

`Stack.env` เป็นไฟล์ local ที่ `.gitignore` และ `.dockerignore` ไม่ให้ commit หรือส่งเป็น Docker build context. ไฟล์ที่ยังไม่มีใน checkout ให้สร้างจาก template บนเครื่องที่ได้รับอนุญาต โดยไม่เขียนทับไฟล์เดิม. นโยบายเหล่านี้ไม่ใช่ secret manager และไม่ลบไฟล์ที่เคยถูก Git ติดตามไว้; ตรวจ `git status` ก่อน commit เสมอ. ค่าที่เว้นว่างเป็น **TBD ต้องกรอกโดยผู้รับผิดชอบ**; ห้ามใส่ secret จริงลง `.example`, Git, chat หรือ logs. จำกัดสิทธิ์ไฟล์/Portainer, ใช้ secure secret manager และลบ working copy ที่ไม่ต้องใช้ตามนโยบาย. บน Linux ตั้งค่า permission ให้ owner เข้าถึงเท่านั้น เช่น `chmod 600` สำหรับไฟล์ที่มี secrets.

## UAT

1. กรอก `SUPERSET_SECRET_KEY` แบบสุ่มอย่างน้อย 32 ตัวอักษร, `INSIGHT_POSTGRES_PASSWORD`, `INSIGHT_ADMIN_USERNAME`, `INSIGHT_ADMIN_EMAIL` และ `INSIGHT_ADMIN_PASSWORD` อย่างน้อย 16 ตัวอักษรจากช่องทางที่ปลอดภัย. Key ต้องคงเดิมและสำรองแยกกับ metadata; รหัสผ่าน admin ใช้ตอนสร้าง account ครั้งแรกเท่านั้น. อย่าเปลี่ยนรหัสผ่าน PostgreSQL ใน env แล้วคาดว่าจะเปลี่ยน account ใน volume เดิม: ต้องทำตามแผน DBA.
2. Template ระบุ UAT image `uat-v1.0.8` ด้วย digest ที่ตรวจ manifest เมื่อ 20 พ.ย. 2026; Release owner ต้องยืนยันก่อนใช้. PostgreSQL และ Redis ค่า override ว่างหมายถึงใช้ digest default จาก Compose. `INSIGHT_PORT=18089` ช่วยหลีกเลี่ยง Redpanda Console default 18088 แต่ยังต้องตรวจว่าพอร์ตว่าง. `INTEGRATION_NETWORK` ต้องตรงกับ external network ที่มีจริง. `INSIGHT_HTTPS_ENABLED=true` เฉพาะหลัง trusted proxy/TLS ใช้งานและตรวจ header controls แล้ว.
   ไม่ต้องเพิ่ม `INSIGHT_POSTGRES_IMAGE` หรือ `INSIGHT_REDIS_IMAGE` ใน Portainer หากใช้ค่า default. ห้ามตั้งสองตัวนี้เป็น Superset image: PostgreSQL ต้องใช้ image PostgreSQL และ Redis ต้องใช้ image Redis ที่มี `redis-server`. หากมี error ว่า `redis-server ... not found` ให้ลบ Redis image override ที่ผิดและตรวจ PostgreSQL image override ด้วย ก่อนลอง deploy อีกครั้ง; ตรวจ containers/volumes ที่อาจถูกสร้างค้าง โดยห้ามลบ volume โดยไม่ตรวจสอบ
3. UAT Compose ส่ง credentials ผ่าน container environment: ผู้ดูแล Docker/Portainer อาจเข้าถึงค่าได้ ต้องจำกัดสิทธิ์และใช้ข้อมูล synthetic/masked. สำหรับ CLI ของ Docker Compose ค่าที่มี `$` หรืออักขระพิเศษต้องจัดรูปแบบ env-file ให้ถูกต้อง; single quotes เป็น literal ตาม [Docker documentation](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/). ทดสอบวิธีนำเข้าใน Portainer เวอร์ชันใช้งานจริงโดยไม่เปิดเผยค่า เพราะการ parse UI อาจแตกต่าง.
4. PostgreSQL/Redis host ports (`INSIGHT_POSTGRES_PUBLISHED_PORT=15433`, `INSIGHT_REDIS_PUBLISHED_PORT=16380`) bind เฉพาะ host loopback. ผู้ใช้จากเครื่องอื่นเข้าผ่าน SSH tunnel ที่อนุมัติตาม [UAT runbook](../../runbooks/07_kingpac_insight_uat.md); Redis UAT ไม่มี authentication/TLS จึงห้ามเปิด direct LAN. ตรวจ port ว่างและเตรียม backup metadata ก่อน redeploy

## Production candidate

กรอก approved image digest, port, Keycloak issuer/client/group และ **absolute paths บน Docker host** ไปยังไฟล์ secret/CA ที่ secret manager จัดเตรียม. ห้ามใส่ password, URL พร้อม credential หรือ private key ลงใน Stack.env. Compose mounts ไฟล์เหล่านี้เป็น `/run/secrets/...` ใน container; permissions ของ host ต้องอนุญาต container UID 1000 อ่านได้ และห้าม world-readable. ตรวจ `insight/prod_preflight.py` เมื่อ process environment ถูกจัดเตรียมอย่างปลอดภัย; script อ่าน environment ไม่ได้อ่าน Stack.env เอง.

PostgreSQL HA, Redis TLS, Keycloak/OIDC และ reverse proxy เป็นบริการภายนอก; endpoint และกลุ่มจริงยังเป็น TBD. การตั้งค่า URI format, CA verification, migration, backup และ rollback อธิบายใน [Production runbook](../../runbooks/08_kingpac_insight_production.md). ค่าใน Stack.env ไม่ได้สร้าง secret files, certificates, database, network หรือบัญชี Keycloak. ระบบ single-host จัดเป็น DEV/UAT ตาม AGENTS.md; ต้องผ่าน HA, data isolation, security, restore และ human approval gates ก่อน production traffic.

## Portainer และการตรวจ Compose

สำหรับ Portainer Docker Standalone เลือก Git repository/ref และ Compose path ของ environment ที่ถูกต้อง จากนั้นกรอก environment ใน UI หรือเลือก **Load variables from .env file** แล้วเลือก protected `Stack.env`; ตรวจข้อมูลก่อน deployment. การนำเข้าไม่ได้หมายความว่า Portainer ดึง Stack.env ที่อยู่ใน Git โดยอัตโนมัติ ดู [Portainer documentation](https://docs.portainer.io/user/docker/stacks/add). อย่านำ UAT และ PROD env มาใช้ปะปนกัน.

ตัวอย่าง syntax check จาก repository root โดยแทน `<secure-path>` ด้วย path ของผู้ดูแลที่เตรียมไว้:

```bash
docker compose --env-file <secure-path>/uat/Stack.env -f compose/docker-compose.insight-uat.yml config --quiet
docker compose --env-file <secure-path>/prod/Stack.env -f compose/docker-compose.insight-prod.yml --profile maintenance config --quiet
```

`config --quiet` ตรวจ Compose interpolation/syntax เท่านั้น ไม่ได้ยืนยันว่ามี secret files จริง, TLS, OIDC, สิทธิ์หรือ image พร้อมใช้งาน. หากยังไม่ได้กรอก required fields การตรวจต้องล้มเหลว; ห้ามใช้ dummy credentials สำหรับ deploy. อย่ารัน `docker compose config` โดยไม่มี `--quiet` กับ secrets จริง เพราะอาจพิมพ์ค่าลง log. การ deploy, migration และ rollback ให้ทำตาม [UAT runbook](../../runbooks/07_kingpac_insight_uat.md) และ [Production runbook](../../runbooks/08_kingpac_insight_production.md) ภายใต้ change ที่ได้รับอนุมัติ
