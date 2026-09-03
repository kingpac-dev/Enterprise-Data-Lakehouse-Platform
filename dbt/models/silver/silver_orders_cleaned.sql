{{ config(
    materialized='table',
    engine='ReplacingMergeTree(_source_updated_at, _is_deleted)',
    order_by=['order_date', 'branch_id', 'order_id'],
    partition_by='toYYYYMM(order_date)'
) }}

-- Cleaned, deduplicated Silver orders layer
SELECT
    order_id,
    customer_id,
    toDate(order_timestamp) AS order_date,
    order_timestamp,
    branch_id,
    product_id,
    unit_price,
    quantity,
    discount,
    round((quantity * unit_price) - discount, 2) AS net_amount,
    upper(status) AS order_status,
    _source_system,
    _source_table,
    _ingested_at,
    _source_updated_at,
    _batch_id,
    _record_hash,
    _is_deleted
FROM {{ source('bronze_raw', 'orders_landing') }}
WHERE _is_deleted = 0
