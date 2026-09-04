"""
PostgreSQL / Relational Database Connector
==========================================
Extracts incremental changes using watermark timestamps or sequential IDs.
"""

import os
from typing import List, Dict, Any, Optional
from .base_connector import BaseConnector


class PostgresConnector(BaseConnector):
    def __init__(
        self,
        pg_conn_string: Optional[str] = None,
        source_system: str = "POSTGRES_PROD",
        source_table: str = "sales_orders",
        watermark_column: str = "updated_at",
        batch_limit: int = 5000,
        **kwargs
    ):
        super().__init__(source_system=source_system, source_table=source_table, **kwargs)
        self.pg_conn_string = pg_conn_string or os.getenv("PG_CONN_STRING", "")
        self.watermark_column = watermark_column
        self.batch_limit = batch_limit

    def extract(self, watermark: Optional[str]) -> List[Dict[str, Any]]:
        """Queries PostgreSQL incrementally above high-watermark."""
        records = []
        try:
            import psycopg2
            import psycopg2.extras

            with psycopg2.connect(self.pg_conn_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    if watermark:
                        sql = f"""
                        SELECT * FROM {self.source_table}
                        WHERE {self.watermark_column} > %s
                        ORDER BY {self.watermark_column} ASC
                        LIMIT %s;
                        """
                        cur.execute(sql, (watermark, self.batch_limit))
                    else:
                        sql = f"""
                        SELECT * FROM {self.source_table}
                        ORDER BY {self.watermark_column} ASC
                        LIMIT %s;
                        """
                        cur.execute(sql, (self.batch_limit,))

                    rows = cur.fetchall()
                    for r in rows:
                        records.append(dict(r))
        except ImportError:
            print(f"[{self.source_system}] Notice: psycopg2 not installed in current environment.")
            print(f"[{self.source_system}] PostgreSQL connector template ready for connection string deployment.")
        except Exception as e:
            print(f"[ERROR] Failed to query PostgreSQL: {e}")

        return records
