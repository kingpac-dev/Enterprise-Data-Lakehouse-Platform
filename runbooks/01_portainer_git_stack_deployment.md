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

### 1. Create Git-Backed Stacks in Portainer
1. Log in to Portainer web interface (`https://<portainer-host>:9443`).
2. Navigate to your target **Environment** -> **Stacks** -> **Add stack**.
3. Select **Repository** as the build method.
4. Fill in repository settings:
   - **Repository URL**: `https://github.com/kingpac-dev/Enterprise-Data-Lakehouse-Platform.git`
   - **Repository reference**: `refs/heads/main` (or specific release tag)
   - **Compose path**:
     - UAT Core (deploy first): `compose/docker-compose.dev.yml`
     - UAT Data Sources: `compose/docker-compose.datasources.yml`
     - UAT Streaming: `compose/docker-compose.streaming.yml`
     - UAT Observability: `compose/docker-compose.observability.yml`
     - For PROD Node 1: `compose/docker-compose.prod-node1.yml`
     - For PROD Node 2: `compose/docker-compose.prod-node2.yml`
     - For PROD Node 3: `compose/docker-compose.prod-keeper3.yml`
   - **Automatic updates**: Enable Webhook or Polling as required by your CI/CD process.

For UAT, create four separate Git-backed stacks in this exact order:

1. `lakehouse-uat-core` — creates the shared `lakehouse-uat-integration` and
   `lakehouse-uat-observability` networks and runs ClickHouse/MinIO.
2. `lakehouse-uat-datasources` — runs PostgreSQL, MySQL, SQL Server, and MongoDB.
3. `lakehouse-uat-streaming` — runs Redpanda and Redpanda Console.
4. `lakehouse-uat-observability` — runs Prometheus, Grafana, and Loki.

Do not deploy the dependent stacks before Core; their external Docker networks will
not exist yet.

### 2. Configure Environment Variables
In each stack's **Environment variables** section, add the applicable values from
`.env.example`. All stacks must use the same `INTEGRATION_NETWORK` and
`OBSERVABILITY_NETWORK` values:

- `CLICKHOUSE_ADMIN_USER`
- `CLICKHOUSE_ADMIN_PASSWORD` (Strong unique secret)
- `S3_ACCESS_KEY` & `S3_SECRET_KEY`
- `GRAFANA_ADMIN_PASSWORD`
- `SOURCE_POSTGRES_PASSWORD`
- `SOURCE_MYSQL_PASSWORD` & `SOURCE_MYSQL_ROOT_PASSWORD`
- `SOURCE_MSSQL_SA_PASSWORD`
- `SOURCE_MSSQL_PASSWORD`
- `SOURCE_MONGODB_ROOT_PASSWORD` & `SOURCE_MONGODB_PASSWORD`
- `REDPANDA_ADVERTISED_HOST` (externally resolvable UAT DNS name or IP)

### 3. Deploy and Verify
1. Click **Deploy the stack**.
2. Portainer clones the repository, injects variables, and runs `docker compose up -d`.
3. Verify all long-running containers report **healthy** or **running** status.
4. Test ClickHouse HTTP ping:
   ```bash
   curl -s http://<host>:18123/ping
   # Expected response: Ok.
   ```

5. Verify the UAT source databases from approved client hosts:
   - PostgreSQL: `<host>:15432`
   - MySQL: `<host>:13306`
   - SQL Server: `<host>:11433`
   - MongoDB: `<host>:17017`

Use internal DNS names and standard container ports between stacks:
`source-postgres:5432`, `source-mysql:3306`, `source-mssql:1433`, and
`source-mongodb:27017`.

The SQL Server initializer creates the configured database and a non-SA
read/write application login. MongoDB creates a non-root application user only
when its data volume is initialized for the first time. Changing MongoDB
credentials in Portainer does not rotate credentials in an existing volume;
perform a governed credential-rotation procedure instead of deleting the volume.

---

## Safe Rollback Procedure
If a deployment fails:
1. In Portainer, edit the stack's **Repository reference** to the previously known working Git commit SHA or tag.
2. Click **Update the stack**.
3. Note: If database migrations were executed, follow the expand/contract guidelines in `AGENTS.md`. Do NOT attempt automatic rollbacks for irreversible schema drops.
