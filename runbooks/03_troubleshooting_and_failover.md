# Runbook 03: Troubleshooting & Failover Procedures

> **UAT scope:** UAT เป็น single host ไม่มี ClickHouse replica/Keeper quorum ให้ failover. หัวข้อ replication/Keeper ด้านล่างใช้กับ production target ที่ผ่าน readiness gate เท่านั้น. สำหรับ 4 stacks ที่ติดตั้งใน UAT ให้ตรวจตาม [คู่มือใช้งาน UAT](../docs/UAT_USER_GUIDE.md), container health, network และ logs ก่อน. คำสั่ง `KILL QUERY`/`OPTIMIZE FINAL` หรือ restart ต้องมี operator review เพราะกระทบ workload.

## 1. Query Errors & Expensive Queries
If `ClickHouseHighQueryErrors` alert fires:
1. Inspect running and recent failed queries:
   ```sql
   SELECT
       event_time,
       user,
       query_duration_ms,
       exception_code,
       exception
   FROM system.query_log
   WHERE type = 'ExceptionWhileProcessing'
   ORDER BY event_time DESC
   LIMIT 10;
   ```
2. Terminate runaway query if needed:
   ```sql
   KILL QUERY WHERE query_id = '<query_id>' SYNC;
   ```

---

## 2. Active Parts Explosion (Merge Backlog)
If `ClickHousePartsExplosion` alert fires (>300 active parts):
1. Identify tables with excessive active parts:
   ```sql
   SELECT
       database,
       table,
       count() AS active_parts,
       formatReadableSize(sum(bytes_on_disk)) AS size
   FROM system.parts
   WHERE active = 1
   GROUP BY database, table
   ORDER BY active_parts DESC
   LIMIT 5;
   ```
2. Root Cause: Usually caused by streaming micro-batch inserts directly into MergeTree without batching.
3. Remediation:
   - Ensure clients enable `async_insert = 1` and `wait_for_async_insert = 1`.
   - Manually trigger partition optimization if needed:
     ```sql
     OPTIMIZE TABLE <database>.<table> FINAL;
     ```

---

## 3. Replication Lag & Read-Only State
If `ClickHouseReplicationQueueLag` alert fires:
1. Inspect replication status:
   ```sql
   SELECT
       database,
       table,
       is_readonly,
       is_session_expired,
       queue_size,
       inserts_in_queue,
       merges_in_queue
   FROM system.replicas;
   ```
2. If `is_readonly = 1`:
   - Verify network connectivity between ClickHouse and Keeper nodes (port 9181).
   - Restart the Keeper service on failed nodes.
   - Once Keeper quorum recovers, ClickHouse automatically exits read-only mode.

---

## 4. Keeper Quorum Loss Recovery
If 2 out of 3 Keeper members become unavailable:
1. Inspect keeper logs:
   ```bash
   docker logs lakehouse-keeper-01 --tail 50
   ```
2. Restart down keeper containers.
3. If data disk corruption occurred on a member, wipe `/var/lib/clickhouse-keeper/coordination` on the single failed container and restart; Keeper will synchronize snapshots from the remaining healthy quorum peers.
