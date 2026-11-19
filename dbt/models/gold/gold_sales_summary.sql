{{ config(
    materialized='table',
    engine='MergeTree()',
    order_by=['order_date', 'branch_id'],
    partition_by='toYYYYMM(order_date)'
) }}

-- Gold domain mart: Aggregated branch daily sales
SELECT
    order_date,
    branch_id,
    count(distinct order_id) AS total_orders,
    count(distinct customer_id) AS total_customers,
    sum(quantity) AS total_units_sold,
    sum(net_amount) AS total_revenue_amount,
    -- Provisional catalog definition: revenue per distinct order, not per line.
    -- Business-owner approval, order identity and upstream deduplication remain required.
    round(sum(net_amount) / nullif(count(distinct order_id), 0), 2) AS average_order_value,
    now64(3) AS _mart_calculated_at
FROM {{ ref('silver_orders_cleaned') }}
WHERE order_status != 'CANCELLED'
GROUP BY order_date, branch_id
