-- =============================================================================
-- 06_lakehouse_open_formats.sql: Lakehouse Open Formats (S3 Parquet & Iceberg)
-- =============================================================================
-- Enables zero-ETL querying directly over external Parquet data lakes and
-- Apache Iceberg table formats stored in S3/MinIO object storage.
-- =============================================================================

-- 1. External Parquet Table over Raw Landing Bucket
-- Allows ClickHouse to scan S3 Parquet landing files directly without local ingestion
CREATE TABLE IF NOT EXISTS raw.ext_s3_orders_landing
(
    order_id UInt64,
    customer_id UInt64,
    order_timestamp DateTime64(3),
    branch_id UInt32,
    product_id UInt64,
    unit_price Decimal(18, 2),
    quantity Decimal(18, 3),
    discount Decimal(18, 2),
    status LowCardinality(String),
    raw_payload String,

    -- Technical Metadata
    _source_system LowCardinality(String),
    _source_table LowCardinality(String),
    _ingested_at DateTime64(3),
    _source_updated_at DateTime64(3),
    _batch_id String,
    _record_hash String,
    _is_deleted UInt8
)
ENGINE = S3(
    'http://minio:9000/lakehouse-landing/landing/*/*/*.parquet',
    'minio_admin',
    'minio_secure_password',
    'Parquet'
);

-- 2. External Parquet Table over Long-Term Cold Archive Bucket
-- Queried for historic analytical audits (3+ years) directly from object storage
CREATE TABLE IF NOT EXISTS mart.ext_s3_sales_archive
(
    order_id UInt64,
    order_timestamp DateTime64(3),
    branch_id UInt32,
    customer_id UInt64,
    product_id UInt64,
    unit_price Decimal(18, 2),
    quantity Decimal(18, 3),
    discount Decimal(18, 2),
    net_amount Decimal(18, 2),
    status LowCardinality(String),
    _source_system LowCardinality(String),
    _ingested_at DateTime64(3)
)
ENGINE = S3(
    'http://minio:9000/lakehouse-landing/archive/sales/*/*.parquet',
    'minio_admin',
    'minio_secure_password',
    'Parquet'
);

-- 3. Apache Iceberg External Table Definition (Template for Iceberg Catalogs)
-- Connects directly to Apache Iceberg metadata stored on S3-compatible lake
CREATE TABLE IF NOT EXISTS raw.ext_iceberg_orders
(
    order_id UInt64,
    customer_id UInt64,
    order_timestamp DateTime64(3),
    branch_id UInt32,
    product_id UInt64,
    unit_price Decimal(18, 2),
    quantity Decimal(18, 3),
    status String
)
ENGINE = Iceberg(
    'http://minio:9000/lakehouse-landing/iceberg/warehouse/orders',
    'minio_admin',
    'minio_secure_password'
);
