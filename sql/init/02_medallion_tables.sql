-- =============================================================================
-- 02_medallion_tables.sql: Medallion Architecture Schemas (Bronze, Silver, Gold)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- BRONZE / RAW LAYER: Source-aligned landing tables
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS raw.orders_landing
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

    -- Mandatory Technical Ingestion Metadata Columns
    _source_system LowCardinality(String),
    _source_table LowCardinality(String),
    _ingested_at DateTime64(3) DEFAULT now64(3),
    _source_updated_at DateTime64(3),
    _batch_id String,
    _record_hash FixedString(32),
    _is_deleted UInt8 DEFAULT 0
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(order_timestamp)
ORDER BY (order_timestamp, branch_id, order_id)
SETTINGS index_granularity = 8192;

-- -----------------------------------------------------------------------------
-- SILVER / CORE LAYER: Cleaned, conformed, deduplicated CDC tables
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS core.dim_customer
(
    customer_id UInt64,
    customer_code String,
    customer_name String,
    customer_segment LowCardinality(String),
    region LowCardinality(String),
    country LowCardinality(String),
    credit_limit Decimal(18, 2),
    is_active UInt8,

    -- CDC Versioning & Metadata
    _source_system LowCardinality(String),
    _source_table LowCardinality(String),
    _ingested_at DateTime64(3) DEFAULT now64(3),
    _source_updated_at DateTime64(3),
    _batch_id String,
    _record_hash FixedString(32),
    _is_deleted UInt8 DEFAULT 0
)
ENGINE = ReplacingMergeTree(_source_updated_at, _is_deleted)
ORDER BY customer_id
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS core.dim_product
(
    product_id UInt64,
    product_sku String,
    product_name String,
    category LowCardinality(String),
    brand LowCardinality(String),
    unit_cost Decimal(18, 2),
    base_price Decimal(18, 2),

    -- CDC Versioning & Metadata
    _source_system LowCardinality(String),
    _source_table LowCardinality(String),
    _ingested_at DateTime64(3) DEFAULT now64(3),
    _source_updated_at DateTime64(3),
    _batch_id String,
    _record_hash FixedString(32),
    _is_deleted UInt8 DEFAULT 0
)
ENGINE = ReplacingMergeTree(_source_updated_at, _is_deleted)
ORDER BY product_id
SETTINGS index_granularity = 8192;

-- -----------------------------------------------------------------------------
-- GOLD / MART LAYER: High-performance business facts & dimensions
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS mart.fact_sales
(
    sale_date Date,
    sale_datetime DateTime64(3),
    order_id UInt64,
    customer_id UInt64,
    product_id UInt64,
    branch_id UInt32,
    quantity Decimal(18, 3),
    unit_price Decimal(18, 2),
    discount_amount Decimal(18, 2),
    amount Decimal(18, 2),

    -- Lineage metadata
    _source_system LowCardinality(String),
    _ingested_at DateTime64(3) DEFAULT now64(3)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(sale_date)
ORDER BY (sale_date, branch_id, product_id, customer_id)
TTL sale_date + INTERVAL 90 DAY TO VOLUME 'cold',
    sale_date + INTERVAL 7 YEAR DELETE
SETTINGS storage_policy = 'hot_to_cold', index_granularity = 8192;
