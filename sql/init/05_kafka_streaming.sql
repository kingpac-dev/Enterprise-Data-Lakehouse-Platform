-- =============================================================================
-- 05_kafka_streaming.sql: Real-Time Event Ingestion via Kafka Engine (M02)
-- =============================================================================
-- Ingests real-time events from Kafka/Redpanda topic 'enterprise.orders.events'
-- and routes them directly into raw.orders_landing with technical metadata.
-- =============================================================================

-- 1. Kafka Engine Consumer Table (Buffer Queue)
CREATE TABLE IF NOT EXISTS raw.kafka_orders_queue
(
    order_id UInt64,
    customer_id UInt64,
    order_timestamp String,
    branch_id UInt32,
    product_id UInt64,
    unit_price Decimal(18, 2),
    quantity Decimal(18, 3),
    discount Decimal(18, 2),
    status String
)
ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'redpanda:29092',
    kafka_topic_list = 'enterprise.orders.events',
    kafka_group_name = 'clickhouse_orders_consumer',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1,
    kafka_max_block_size = 1048576,
    kafka_skip_broken_messages = 100;

-- 2. Materialized View to Stream from Kafka Queue into raw.orders_landing
CREATE MATERIALIZED VIEW IF NOT EXISTS raw.mv_kafka_orders_to_landing TO raw.orders_landing AS
SELECT
    order_id,
    customer_id,
    parseDateTime64BestEffortOrZero(order_timestamp, 3) AS order_timestamp,
    branch_id,
    product_id,
    unit_price,
    quantity,
    discount,
    status,
    concat('{"source": "kafka", "order_id": ', toString(order_id), '}') AS raw_payload,

    -- Mandatory Technical Ingestion Metadata Columns
    'kafka_stream' AS _source_system,
    'enterprise.orders.events' AS _source_table,
    now64(3) AS _ingested_at,
    now64(3) AS _source_updated_at,
    concat('stream_', toString(toUnixTimestamp64Milli(now64(3)))) AS _batch_id,
    MD5(concat(toString(order_id), toString(order_timestamp))) AS _record_hash,
    0 AS _is_deleted
FROM raw.kafka_orders_queue;
