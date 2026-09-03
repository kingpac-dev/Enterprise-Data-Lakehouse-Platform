-- =============================================================================
-- 03_materialized_views.sql: High-Performance Serving Layer & Pre-aggregations
-- =============================================================================

-- Target pre-aggregated table for Daily Branch Sales
CREATE TABLE IF NOT EXISTS serving.daily_branch_sales_mv_target
(
    sale_date Date,
    branch_id UInt32,
    total_orders AggregateFunction(count, UInt64),
    total_quantity AggregateFunction(sum, Decimal(18, 3)),
    total_revenue AggregateFunction(sum, Decimal(18, 2)),
    unique_customers AggregateFunction(uniqExact, UInt64)
)
ENGINE = AggregatingMergeTree
PARTITION BY toYYYYMM(sale_date)
ORDER BY (sale_date, branch_id);

-- Materialized View populating target table in real-time upon fact insertion
CREATE MATERIALIZED VIEW IF NOT EXISTS serving.mv_daily_branch_sales
TO serving.daily_branch_sales_mv_target
AS
SELECT
    sale_date,
    branch_id,
    countState(order_id) AS total_orders,
    sumState(quantity) AS total_quantity,
    sumState(amount) AS total_revenue,
    uniqExactState(customer_id) AS unique_customers
FROM mart.fact_sales
GROUP BY sale_date, branch_id;

-- Fast Serving View for BI / Dashboard Consumption (Zero scanning of raw rows)
CREATE OR REPLACE VIEW serving.v_daily_branch_sales AS
SELECT
    sale_date,
    branch_id,
    countMerge(total_orders) AS total_orders,
    sumMerge(total_quantity) AS total_quantity,
    sumMerge(total_revenue) AS total_revenue,
    uniqExactMerge(unique_customers) AS unique_customers
FROM serving.daily_branch_sales_mv_target
GROUP BY sale_date, branch_id;
