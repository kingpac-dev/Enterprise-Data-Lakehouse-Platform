"""Fast semantic regression check; this does not replace ClickHouse/dbt tests."""

import re
import sqlite3
import unittest
from pathlib import Path


class SalesAOVTest(unittest.TestCase):
    def test_multiline_order_and_cancelled_order(self):
        path = Path(__file__).resolve().parents[1] / "models" / "gold" / "gold_sales_summary.sql"
        sql = path.read_text(encoding="utf-8")
        sql = re.sub(r"\{\{\s*config\(.*?\)\s*\}\}", "", sql, count=1, flags=re.DOTALL)
        sql = re.sub(r"\{\{\s*ref\('silver_orders_cleaned'\)\s*\}\}", "orders_fixture", sql)
        # The timestamp is not compared; SQLite has no ClickHouse now64 function.
        sql = sql.replace("now64(3)", "CURRENT_TIMESTAMP")
        with sqlite3.connect(":memory:") as connection:
            connection.execute("""CREATE TABLE orders_fixture (
                order_date TEXT, branch_id INTEGER, order_id INTEGER, customer_id INTEGER,
                quantity REAL, net_amount REAL, order_status TEXT)""")
            connection.executemany("INSERT INTO orders_fixture VALUES (?, ?, ?, ?, ?, ?, ?)", [
                ("2026-01-15", 1, 101, 10, 1, 60, "COMPLETED"),
                ("2026-01-15", 1, 101, 10, 1, 20, "COMPLETED"),
                ("2026-01-15", 1, 102, 11, 1, 20, "SHIPPED"),
                ("2026-01-15", 1, 103, 12, 1, 900, "CANCELLED"),
            ])
            rows = connection.execute(sql).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][:7], ("2026-01-15", 1, 2, 2, 3, 100, 50))


if __name__ == "__main__":
    unittest.main()
