"""
Sales & Serving Endpoints Router
================================
Provides governed, sub-second API access to ClickHouse serving views.
"""

import os
import json
import urllib.request
import urllib.error
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

router = APIRouter(prefix="/api/v1/sales", tags=["Sales Serving"])

CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT_HTTP", "8123"))
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_API_USER", "api_user")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_API_PASSWORD", "change_this_api_password_in_prod")


def clickhouse_query_json(sql: str):
    """Executes query and returns parsed JSON array."""
    url = f"http://{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/?query={urllib.parse.quote(sql.strip())}%20FORMAT%20JSON"
    headers = {
        "X-ClickHouse-User": CLICKHOUSE_USER,
        "X-ClickHouse-Key": CLICKHOUSE_PASSWORD,
        "X-ClickHouse-Setting": "max_execution_time=10,readonly=1",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", [])
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        raise HTTPException(status_code=500, detail=f"ClickHouse query error: {err_msg}")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"ClickHouse unavailable: {e}")


@router.get("/daily-summary")
def get_daily_sales_summary(
    days: int = Query(7, ge=1, le=90, description="Lookback window in days"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
):
    """Fetches pre-aggregated daily branch sales from serving view."""
    sql = f"""
    SELECT
        sale_date,
        branch_id,
        total_orders,
        total_quantity,
        total_revenue,
        unique_customers
    FROM serving.v_daily_branch_sales
    WHERE sale_date >= today() - INTERVAL {days} DAY
    ORDER BY sale_date DESC, total_revenue DESC
    LIMIT {limit}
    """
    return {
        "status": "success",
        "data": clickhouse_query_json(sql),
    }


@router.get("/branch/{branch_id}")
def get_branch_sales(
    branch_id: int,
    days: int = Query(30, ge=1, le=180, description="Lookback days"),
):
    """Fetches specific branch performance."""
    sql = f"""
    SELECT
        sale_date,
        branch_id,
        total_orders,
        total_quantity,
        total_revenue,
        unique_customers
    FROM serving.v_daily_branch_sales
    WHERE branch_id = {branch_id}
      AND sale_date >= today() - INTERVAL {days} DAY
    ORDER BY sale_date DESC
    """
    data = clickhouse_query_json(sql)
    return {
        "status": "success",
        "branch_id": branch_id,
        "data": data,
    }


@router.get("/top-products")
def get_top_products(
    limit: int = Query(10, ge=1, le=100),
):
    """Fetches top-selling products from Gold Fact & Core Product dimensions."""
    sql = f"""
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        count() AS total_transactions,
        sum(f.quantity) AS units_sold,
        sum(f.amount) AS total_revenue
    FROM mart.fact_sales AS f
    JOIN core.dim_product AS p ON f.product_id = p.product_id
    GROUP BY p.product_id, p.product_name, p.category
    ORDER BY total_revenue DESC
    LIMIT {limit}
    """
    return {
        "status": "success",
        "data": clickhouse_query_json(sql),
    }
