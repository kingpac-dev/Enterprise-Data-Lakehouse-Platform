-- Custom test: Ensure net sales amounts in gold summary cannot be negative
SELECT
    order_date,
    branch_id,
    total_revenue_amount
FROM {{ ref('gold_sales_summary') }}
WHERE total_revenue_amount < 0
