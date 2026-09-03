# ADR-0001: Storage Separation and Parquet as Lake Format

## Status
Accepted

## Context
The Enterprise Data Lakehouse Platform requires a cost-effective, scalable, and durable foundation to store immutable raw landing files, historical archives, and backup snapshots while enabling high-performance sub-second analytical queries. Retaining petabyte-scale raw data exclusively on high-performance NVMe drives attached to ClickHouse compute nodes is prohibitively expensive and tightly couples storage growth to compute costs.

## Decision
1. **Decouple Storage and Compute**:
   - Utilize S3-compatible object storage (MinIO for DEV/UAT; enterprise object storage such as Ceph, ECS, or AWS S3 for PROD) as the durable persistence layer for Landing, Bronze raw archive, and backup snapshots.
   - Use high-performance local NVMe/SSD disks for ClickHouse hot active partitions and materialized views.
2. **Standard Lake Format**:
   - Adopt **Apache Parquet** as the default open columnar format for lake storage due to its high compression ratio, open ecosystem compatibility, and native ClickHouse integration (`S3` engine and `s3Cluster` functions).
   - Evaluate Apache Iceberg table format for Phase 2 once multi-engine transactional metadata requirements are established.

## Consequences
### Positive
- Independent scaling of storage volume and analytical compute capacity.
- Significantly reduced total cost of ownership (TCO) by tiering older data to object storage.
- Interoperability with broader data ecosystem (Spark, Trino, Python/DuckDB).

### Negative / Trade-offs
- Reading cold partitions directly from object storage incurs higher network latency compared to local NVMe.
- Requires robust storage policy and volume caching configurations within ClickHouse.
