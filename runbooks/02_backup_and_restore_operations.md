# Runbook 02: ClickHouse Backup, Restore & DR Drill

## Operational Principle
> "A backup is not considered reliable until restore testing has been demonstrated with measured recovery evidence."

**UAT implementation ปัจจุบัน:** [`backup_clickhouse.sh`](../scripts/backup_clickhouse.sh) สำรองทั้ง database `mart` ไป S3; [`restore_test.sh`](../scripts/restore_test.sh) restore เป็น database `drill_restore`, เปรียบเทียบเฉพาะ row count ของ `fact_sales` แล้วสั่ง `DROP DATABASE drill_restore`. SQL ตัวอย่างด้านล่างเป็น reference สำหรับการออกแบบ drill เพิ่มเติม **ไม่ใช่ output ที่ scripts รันอยู่**. ค่า default UAT ชี้ MinIO บน host เดียว จึงไม่ใช่ independent DR destination. ดู [คู่มือใช้งาน UAT](../docs/UAT_USER_GUIDE.md#13-backup-restore-และ-dr) และยืนยันว่า `drill_restore` ว่างก่อนรัน script; ตรวจ HTTP/SQL result และ object จริง เพราะข้อความ success จาก shell อย่างเดียวไม่เพียงพอ.

---

## 1. Automated Native Backup to S3
ClickHouse 26.8 LTS supports native backups directly to S3-compatible object storage. ตัวอย่าง `async = false` ด้านล่างรอผลคำสั่ง; ต้องตรวจ result จาก ClickHouse จริง.

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
Run row-count and revenue-total reconciliation (ยังไม่ใช่ checksum ของข้อมูลทุกแถว):
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
