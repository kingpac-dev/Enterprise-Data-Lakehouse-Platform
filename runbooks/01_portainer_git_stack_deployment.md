# Runbook 01: Governed Portainer Git Stack Deployment

## Objective
Deploy and update the Enterprise Data Lakehouse Platform stacks using **Portainer Git-backed Stacks** to ensure all infrastructure changes remain traceable, auditable, and version-controlled.

---

## Prerequisites
1. Ubuntu 24 LTS host running Docker Engine and Portainer Server or Portainer Agent.
2. Network access from Portainer to this Git repository (via HTTPS token or SSH deploy key).
3. Secrets populated in the Portainer Stack Environment Variables interface (never committed into Git).

---

## Deployment Steps

### 1. Create Git-Backed Stack in Portainer
1. Log in to Portainer web interface (`https://<portainer-host>:9443`).
2. Navigate to your target **Environment** -> **Stacks** -> **Add stack**.
3. Select **Repository** as the build method.
4. Fill in repository settings:
   - **Repository URL**: `https://github.com/kingpac-dev/Enterprise-Data-Lakehouse-Platform.git`
   - **Repository reference**: `refs/heads/main` (or specific release tag)
   - **Compose path**:
     - For DEV/UAT: `compose/docker-compose.dev.yml`
     - For PROD Node 1: `compose/docker-compose.prod-node1.yml`
     - For PROD Node 2: `compose/docker-compose.prod-node2.yml`
     - For PROD Node 3: `compose/docker-compose.prod-keeper3.yml`
   - **Automatic updates**: Enable Webhook or Polling as required by your CI/CD process.

### 2. Configure Environment Variables
In the **Environment variables** section of the stack, add values matching `.env.example`:
- `CLICKHOUSE_ADMIN_USER`
- `CLICKHOUSE_ADMIN_PASSWORD` (Strong unique secret)
- `S3_ACCESS_KEY` & `S3_SECRET_KEY`
- `GRAFANA_ADMIN_PASSWORD`

### 3. Deploy and Verify
1. Click **Deploy the stack**.
2. Portainer clones the repository, injects variables, and runs `docker compose up -d`.
3. Verify all containers are reporting **healthy** status.
4. Test ClickHouse HTTP ping:
   ```bash
   curl -s http://<host>:8123/ping
   # Expected response: Ok.
   ```

---

## Safe Rollback Procedure
If a deployment fails:
1. In Portainer, edit the stack's **Repository reference** to the previously known working Git commit SHA or tag.
2. Click **Update the stack**.
3. Note: If database migrations were executed, follow the expand/contract guidelines in `AGENTS.md`. Do NOT attempt automatic rollbacks for irreversible schema drops.
