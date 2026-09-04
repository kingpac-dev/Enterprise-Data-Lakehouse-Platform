#!/usr/bin/env python3
"""
Enterprise Governed AI Text-to-SQL Assistant
============================================
Translates natural language analytical questions into guarded, performant
ClickHouse SQL using the semantic metric catalog.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from .guardrails import validate_sql_guardrails

CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT_HTTP", "8123"))
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_BI_USER", "bi_user")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_BI_PASSWORD", "change_this_bi_password_in_prod")


# Semantic intent pattern dictionary
INTENTS = {
    "daily_revenue": {
        "keywords": ["revenue", "sales", "daily", "trend", "รายได้", "ยอดขายรายวัน"],
        "sql": """
        SELECT
            sale_date,
            sumMerge(total_revenue) AS daily_revenue,
            sumMerge(total_orders) AS daily_orders
        FROM serving.daily_branch_sales_mv_target
        WHERE sale_date >= today() - INTERVAL 14 DAY
        GROUP BY sale_date
        ORDER BY sale_date DESC
        LIMIT 14
        """
    },
    "top_branches": {
        "keywords": ["branch", "top", "performance", "สาขา", "ยอดขายตามสาขา"],
        "sql": """
        SELECT
            branch_id,
            sum(amount) AS branch_revenue,
            count(distinct order_id) AS total_orders
        FROM mart.fact_sales
        WHERE sale_date >= today() - INTERVAL 30 DAY
        GROUP BY branch_id
        ORDER BY branch_revenue DESC
        LIMIT 5
        """
    },
    "aov": {
        "keywords": ["average order", "aov", "ticket", "ยอดต่อบิล", "เฉลี่ย"],
        "sql": """
        SELECT
            toYYYYMM(sale_date) AS month,
            round(sum(amount) / nullif(count(distinct order_id), 0), 2) AS average_order_value
        FROM mart.fact_sales
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
        """
    }
}


def translate_nl_to_sql(question: str) -> str:
    """Matches intent and constructs vetted SQL."""
    q_lower = question.lower()
    for intent, config in INTENTS.items():
        if any(kw in q_lower for kw in config["keywords"]):
            return config["sql"].strip()

    # Fallback to general serving summary
    return """
    SELECT
        sale_date,
        branch_id,
        total_revenue,
        total_orders
    FROM serving.v_daily_branch_sales
    WHERE sale_date >= today() - INTERVAL 7 DAY
    ORDER BY sale_date DESC
    LIMIT 20
    """.strip()


def execute_guarded_query(sql: str):
    """Validates query against security guardrails and executes it."""
    is_valid, message, sanitized_sql = validate_sql_guardrails(sql)
    if not is_valid:
        print(f"[SECURITY BLOCKED] {message}")
        return {"status": "blocked", "reason": message}

    print(f"[GUARDRAILS PASSED] Executing sanitized query:\n{sanitized_sql}\n")
    url = f"http://{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/?query={urllib.parse.quote(sanitized_sql)}%20FORMAT%20PrettyCompact"
    headers = {
        "X-ClickHouse-User": CLICKHOUSE_USER,
        "X-ClickHouse-Key": CLICKHOUSE_PASSWORD,
        "X-ClickHouse-Setting": "max_execution_time=15,readonly=1",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = resp.read().decode("utf-8")
            return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def ask_ai(question: str):
    print("=" * 70)
    print(f"User Question: \"{question}\"")
    print("-" * 70)
    sql = translate_nl_to_sql(question)
    res = execute_guarded_query(sql)
    if res.get("status") == "success":
        print("Query Results:")
        print(res.get("result"))
    elif res.get("status") == "blocked":
        print(f"Query Blocked by Guardrail: {res.get('reason')}")
    else:
        print(f"Query Error: {res.get('error')}")
    print("=" * 70)


if __name__ == "__main__":
    test_q = sys.argv[1] if len(sys.argv) > 1 else "แสดงยอดขายรายวัน 14 วันล่าสุด"
    ask_ai(test_q)
