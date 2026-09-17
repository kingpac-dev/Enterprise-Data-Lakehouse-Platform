#!/usr/bin/env bash
# ==============================================================================
# ClickHouse Automated S3 Backup Script
# ==============================================================================
set -euo pipefail

BACKUP_DATE=$(date -u +"%Y%m%d_%H%M%S")
CLICKHOUSE_HOST="${CLICKHOUSE_HOST:-127.0.0.1}"
CLICKHOUSE_PORT="${CLICKHOUSE_PORT_HTTP:-18123}"
CLICKHOUSE_USER="${CLICKHOUSE_ADMIN_USER:-admin}"
CLICKHOUSE_PASSWORD="${CLICKHOUSE_ADMIN_PASSWORD:-change_this_admin_password_in_prod}"

S3_ENDPOINT="${S3_ENDPOINT:-minio:9000}"
S3_BUCKET="${S3_BUCKET_LAKE:-enterprise-data-lake}"
S3_ACCESS_KEY="${S3_ACCESS_KEY:-lakehouse_s3_access_key}"
S3_SECRET_KEY="${S3_SECRET_KEY:-lakehouse_s3_secret_change_me}"

BACKUP_DEST="http://${S3_ENDPOINT}/${S3_BUCKET}/backup/clickhouse/backup_${BACKUP_DATE}/"

echo "=== [$(date)] Starting ClickHouse Backup to ${BACKUP_DEST} ==="

SQL_BACKUP="BACKUP DATABASE mart TO S3('${BACKUP_DEST}', '${S3_ACCESS_KEY}', '${S3_SECRET_KEY}') SETTINGS async = false;"

curl -sS -u "${CLICKHOUSE_USER}:${CLICKHOUSE_PASSWORD}" \
  -d "${SQL_BACKUP}" \
  "http://${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/"

echo "=== [$(date)] Backup Completed Successfully: backup_${BACKUP_DATE} ==="
