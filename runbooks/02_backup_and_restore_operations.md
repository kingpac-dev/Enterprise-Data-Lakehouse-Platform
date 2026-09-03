# Runbook 02: ClickHouse Backup, Restore & DR Drill

## Operational Principle
> "A backup is not considered reliable until restore testing has been demonstrated with measured recovery evidence."

---

## 1. Automated Native Backup to S3
ClickHouse 26.8 LTS supports native, non-blocking backups directly to S3-compatible object storage.

### Backup Command Syntax:
```sql
BACKUP TABLE mart.fact_sales
TO S3(
    'http://minio:9000/enterprise-data-lake/backup/clickhouse/fact_sales_{DATE}/',
    '${S3_ACCESS_KEY}',
    '${S3_SECRET_KEY}'
)
SETTINGS async = false;
```

### Full Database Backup Syntax:
```sql
BACKUP DATABASE mart
TO S3(
    'http://minio:9000/enterprise-data-lake/backup/clickhouse/mart_backup_{DATE}/',
    '${S3_ACCESS_KEY}',
    '${S3_SECRET_KEY}'
);
```

---

## 2. Non-Destructive Restore Drill Procedure
Execute quarterly in an isolated non-production environment:

### Step 1: Pre-Restore Record Count
Query source table:
```sql
SELECT count() AS source_count, sum(amount) AS source_revenue FROM mart.fact_sales;
```

### Step 2: Restore to Staging Verification Table
Restore the backup into a separate database (`raw` or dedicated drill database):
```sql
RESTORE TABLE mart.fact_sales AS mart.fact_sales_restore_test
FROM S3(
    'http://minio:9000/enterprise-data-lake/backup/clickhouse/fact_sales_{DATE}/',
    '${S3_ACCESS_KEY}',
    '${S3_SECRET_KEY}'
);
```

### Step 3: Reconciliation & Integrity Check
Run checksum reconciliation:
```sql
SELECT
    (SELECT count() FROM mart.fact_sales) AS original_rows,
    (SELECT count() FROM mart.fact_sales_restore_test) AS restored_rows,
    (SELECT sum(amount) FROM mart.fact_sales) AS original_revenue,
    (SELECT sum(amount) FROM mart.fact_sales_restore_test) AS restored_revenue;
```

### Step 4: Cleanup
Drop the temporary verification table:
```sql
DROP TABLE IF EXISTS mart.fact_sales_restore_test;
```

### Step 5: Record Drill Evidence
Log in the DR Audit Register:
- Date & Time
- Operator Name
- Backup Size (bytes)
- Restore Duration (seconds) -> Compare against RTO <= 4 hours
- Row Count Discrepancies (must be 0)
