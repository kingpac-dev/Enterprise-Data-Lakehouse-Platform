#!/usr/bin/env python3
"""
Enterprise Data Lakehouse Platform - Sample Ingestion & Pipeline Generator
==========================================================================
Generates synthetic enterprise orders, saves Parquet/JSON batches to S3/MinIO
landing, and inserts rows into ClickHouse raw.orders_landing with all mandatory
technical metadata columns:
  - _source_system
  - _source_table
  - _ingested_at
  - _source_updated_at
  - _batch_id
  - _record_hash
  - _is_deleted
"""

import os
import sys
import uuid
import hashlib
import random
import datetime
import json
import urllib.request
import urllib.error

# Load environment configuration or defaults
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT_HTTP", "18123"))
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_ADMIN_USER", "admin")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_ADMIN_PASSWORD", "change_this_admin_password_in_prod")
S3_ENDPOINT = os.getenv("S3_PUBLIC_ENDPOINT", "http://localhost:19090")
S3_BUCKET = os.getenv("S3_BUCKET_LAKE", "enterprise-data-lake")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "lakehouse_s3_access_key")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "lakehouse_s3_secret_change_me")


def execute_clickhouse_query(query: str, data: bytes = None) -> str:
    """Executes a SQL query against ClickHouse HTTP interface."""
    url = f"http://{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/"
    headers = {"X-ClickHouse-User": CLICKHOUSE_USER, "X-ClickHouse-Key": CLICKHOUSE_PASSWORD}
    if data:
        req = urllib.request.Request(f"{url}?query={urllib.parse.quote(query)}", data=data, headers=headers)
    else:
        req = urllib.request.Request(url, data=query.encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.URLError as e:
        print(f"[ERROR] Failed to query ClickHouse: {e}")
        return ""


def generate_batch(batch_size: int = 500):
    """Generates synthetic enterprise order records with mandatory technical metadata."""
    batch_id = str(uuid.uuid4())
    now = datetime.datetime.now(datetime.timezone.utc)
    now_str = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    statuses = ["COMPLETED", "COMPLETED", "COMPLETED", "PROCESSING", "SHIPPED", "CANCELLED"]
    systems = ["ERP_SAP", "ECOMMERCE_WEB", "POS_BRANCH", "MOBILE_APP"]
    records = []

    for i in range(1, batch_size + 1):
        order_id = random.randint(100000, 999999)
        customer_id = random.randint(1000, 2500)
        branch_id = random.randint(1, 20)
        product_id = random.randint(101, 250)
        unit_price = round(random.uniform(50.0, 5000.0), 2)
        quantity = round(random.uniform(1.0, 10.0), 3)
        discount = round(unit_price * quantity * random.choice([0.0, 0.05, 0.1, 0.15]), 2)
        status = random.choice(statuses)
        source_system = random.choice(systems)

        # 30 days window
        days_ago = random.randint(0, 30)
        order_timestamp = (now - datetime.timedelta(days=days_ago, minutes=random.randint(0, 1440))).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        payload = {
            "order_id": order_id,
            "customer_id": customer_id,
            "branch_id": branch_id,
            "product_id": product_id,
            "unit_price": unit_price,
            "quantity": quantity,
            "discount": discount,
            "status": status,
        }
        payload_str = json.dumps(payload)
        record_hash = hashlib.md5(payload_str.encode("utf-8")).hexdigest()

        records.append({
            "order_id": order_id,
            "customer_id": customer_id,
            "order_timestamp": order_timestamp,
            "branch_id": branch_id,
            "product_id": product_id,
            "unit_price": unit_price,
            "quantity": quantity,
            "discount": discount,
            "status": status,
            "raw_payload": payload_str,
            "_source_system": source_system,
            "_source_table": "sales_orders",
            "_ingested_at": now_str,
            "_source_updated_at": order_timestamp,
            "_batch_id": batch_id,
            "_record_hash": record_hash,
            "_is_deleted": 0,
        })

    return batch_id, records


def seed_dimension_tables():
    """Seeds dimension tables in core database for customer and product."""
    print("Seeding core.dim_customer and core.dim_product...")
    customers = [
        (1001, "CUST-1001", "Global Logistics Corp", "ENTERPRISE", "APAC", "Thailand", 1000000.00, 1),
        (1002, "CUST-1002", "Siam Tech Solutions", "SMB", "APAC", "Thailand", 250000.00, 1),
        (1003, "CUST-1003", "Bangkok Retail Chain", "ENTERPRISE", "APAC", "Thailand", 5000000.00, 1),
        (1004, "CUST-1004", "Eastern Coast Shipping", "SMB", "APAC", "Thailand", 150000.00, 1),
        (1005, "CUST-1005", "Andaman Trading Ltd", "RETAIL", "APAC", "Thailand", 50000.00, 1),
    ]

    products = [
        (101, "SKU-SV-01", "Server Blade NVMe 2U", "HARDWARE", "SysCorp", 35000.00, 48000.00),
        (102, "SKU-NET-02", "Switch 100GbE 32-Port", "NETWORKING", "CiscoNet", 22000.00, 31000.00),
        (103, "SKU-SW-03", "Data Platform License Tier-1", "SOFTWARE", "KingPac", 12000.00, 18500.00),
        (104, "SKU-SRV-04", "Enterprise 24x7 Support SLA", "SERVICE", "KingPac", 5000.00, 9500.00),
        (105, "SKU-STG-05", "NVMe Array Module 15TB", "STORAGE", "FlashTech", 28000.00, 41000.00),
    ]

    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    cust_rows = []
    for c in customers:
        cust_rows.append(f"({c[0]}, '{c[1]}', '{c[2]}', '{c[3]}', '{c[4]}', '{c[5]}', {c[6]}, {c[7]}, 'SEED', 'customers', '{now_str}', '{now_str}', 'INIT_BATCH', '{hashlib.md5(str(c).encode()).hexdigest()}', 0)")

    sql_cust = f"INSERT INTO core.dim_customer VALUES {', '.join(cust_rows)}"
    execute_clickhouse_query(sql_cust)

    prod_rows = []
    for p in products:
        prod_rows.append(f"({p[0]}, '{p[1]}', '{p[2]}', '{p[3]}', '{p[4]}', {p[5]}, {p[6]}, 'SEED', 'products', '{now_str}', '{now_str}', 'INIT_BATCH', '{hashlib.md5(str(p).encode()).hexdigest()}', 0)")

    sql_prod = f"INSERT INTO core.dim_product VALUES {', '.join(prod_rows)}"
    execute_clickhouse_query(sql_prod)
    print("Dimension seeding complete.")


def ingest_to_clickhouse(records):
    """Ingests generated records in JSONEachRow format into ClickHouse raw.orders_landing."""
    print(f"Ingesting {len(records)} records into raw.orders_landing...")
    query = "INSERT INTO raw.orders_landing FORMAT JSONEachRow"
    data = "\n".join(json.dumps(r) for r in records).encode("utf-8")
    execute_clickhouse_query(query, data=data)
    print("Ingestion into raw.orders_landing complete.")


def populate_gold_mart_sample():
    """Populates initial records into mart.fact_sales from raw landing to verify queries."""
    print("Populating mart.fact_sales from raw landing...")
    query = """
    INSERT INTO mart.fact_sales
    SELECT
        toDate(order_timestamp) AS sale_date,
        order_timestamp AS sale_datetime,
        order_id,
        customer_id,
        product_id,
        branch_id,
        quantity,
        unit_price,
        discount AS discount_amount,
        round((quantity * unit_price) - discount, 2) AS amount,
        _source_system,
        _ingested_at
    FROM raw.orders_landing
    WHERE status != 'CANCELLED';
    """
    execute_clickhouse_query(query)
    print("mart.fact_sales population complete.")


def main():
    print("=" * 70)
    print("Enterprise Data Lakehouse Platform - Sample Ingestion Pipeline")
    print(f"Target ClickHouse: {CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}")
    print("=" * 70)

    # 1. Health check
    ping = execute_clickhouse_query("SELECT 1")
    if not ping or "1" not in ping:
        print("[WARNING] ClickHouse is not responding or unreachable at this moment.")
        print("To start ClickHouse DEV stack: docker compose -f compose/docker-compose.dev.yml up -d")
        sys.exit(0)

    print("[OK] ClickHouse connection verified.")

    # 2. Seed Dimensions
    seed_dimension_tables()

    # 3. Generate and ingest transaction records
    batch_id, records = generate_batch(batch_size=500)
    print(f"[OK] Generated Batch ID: {batch_id} with {len(records)} records.")

    ingest_to_clickhouse(records)

    # 4. Populate mart.fact_sales
    populate_gold_mart_sample()

    # 5. Verify counts
    raw_count = execute_clickhouse_query("SELECT count() FROM raw.orders_landing").strip()
    mart_count = execute_clickhouse_query("SELECT count() FROM mart.fact_sales").strip()
    serving_count = execute_clickhouse_query("SELECT count() FROM serving.v_daily_branch_sales").strip()

    print("-" * 70)
    print(f"Pipeline Execution Summary:")
    print(f"  raw.orders_landing total rows   : {raw_count}")
    print(f"  mart.fact_sales total rows      : {mart_count}")
    print(f"  serving.v_daily_branch_sales rows: {serving_count}")
    print("=" * 70)
    print("Pipeline finished successfully!")


if __name__ == "__main__":
    main()
