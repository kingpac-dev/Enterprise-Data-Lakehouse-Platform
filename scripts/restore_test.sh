#!/usr/bin/env bash
# ==============================================================================
# Non-Destructive Restore Drill & Reconciliation Script
# ==============================================================================
set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "Usage: $0 <backup_name_or_date>"
  echo "Example: $0 20260903_120000"
  exit 1
fi

BACKUP_ID="$1"
CLICKHOUSE_HOST="${CLICKHOUSE_HOST:-127.0.0.1}"
CLICKHOUSE_PORT="${CLICKHOUSE_PORT_HTTP:-18123}"
CLICKHOUSE_USER="${CLICKHOUSE_ADMIN_USER:-admin}"
CLICKHOUSE_PASSWORD="${CLICKHOUSE_ADMIN_PASSWORD:-change_this_admin_password_in_prod}"

S3_ENDPOINT="${S3_ENDPOINT:-minio:9000}"
S3_BUCKET="${S3_BUCKET_LAKE:-enterprise-data-lake}"
S3_ACCESS_KEY="${S3_ACCESS_KEY:-lakehouse_s3_access_key}"
S3_SECRET_KEY="${S3_SECRET_KEY:-lakehouse_s3_secret_change_me}"

BACKUP_SRC="http://${S3_ENDPOINT}/${S3_BUCKET}/backup/clickhouse/backup_${BACKUP_ID}/"

START_TIME=$(date +%s)
echo "=== Starting Non-Destructive Restore Drill from ${BACKUP_SRC} ==="

# 1. Restore to drill database
SQL_CREATE_DB="CREATE DATABASE IF NOT EXISTS drill_restore;"
curl -sS -u "${CLICKHOUSE_USER}:${CLICKHOUSE_PASSWORD}" -d "${SQL_CREATE_DB}" "http://${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/"

SQL_RESTORE="RESTORE DATABASE mart AS drill_restore FROM S3('${BACKUP_SRC}', '${S3_ACCESS_KEY}', '${S3_SECRET_KEY}');"
curl -sS -u "${CLICKHOUSE_USER}:${CLICKHOUSE_PASSWORD}" -d "${SQL_RESTORE}" "http://${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/"

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

# 2. Reconciliation check
ORIGINAL_ROWS=$(curl -sS -u "${CLICKHOUSE_USER}:${CLICKHOUSE_PASSWORD}" -d "SELECT count() FROM mart.fact_sales" "http://${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/")
RESTORED_ROWS=$(curl -sS -u "${CLICKHOUSE_USER}:${CLICKHOUSE_PASSWORD}" -d "SELECT count() FROM drill_restore.fact_sales" "http://${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/")

echo "--- Reconciliation Results ---"
echo "Original Rows: ${ORIGINAL_ROWS}"
echo "Restored Rows: ${RESTORED_ROWS}"
echo "Restore Elapsed Time: ${ELAPSED} seconds"

if [ "${ORIGINAL_ROWS}" -eq "${RESTORED_ROWS}" ]; then
  echo ">>> DRILL PASSED: Row counts match perfectly! <<<"
else
  echo ">>> DRILL FAILED: Discrepancy detected! <<<"
fi

# 3. Cleanup drill database
curl -sS -u "${CLICKHOUSE_USER}:${CLICKHOUSE_PASSWORD}" -d "DROP DATABASE IF EXISTS drill_restore SYNC;" "http://${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/"
echo "=== Cleanup completed. Restore drill complete. ==="
