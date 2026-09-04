"""
=============================================================================
Enterprise Data Lakehouse Platform - Apache Airflow / Composer DAG (M06)
=============================================================================
Defines the daily production ELT and governance DAG for Airflow 2.8+ / Cloud Composer.
DAG: enterprise_lakehouse_daily_pipeline
Schedule: @daily (02:00 UTC)
Dependencies:
  ingest_orders_landing >> dbt_silver_gold_transform >> dbt_quality_tests >> reconcile_layers >> backup_snapshot
"""

from datetime import datetime, timedelta

try:
    from airflow import DAG
    from airflow.operators.bash import BashOperator
    from airflow.operators.python import PythonOperator
    from airflow.utils.dates import days_ago
    AIRFLOW_AVAILABLE = True
except ImportError:
    AIRFLOW_AVAILABLE = False

# Default DAG arguments
default_args = {
    "owner": "data_engineering",
    "depends_on_past": False,
    "email": ["data-ops-alerts@enterprise.internal"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=3),
    "execution_timeout": timedelta(minutes=45),
}

if AIRFLOW_AVAILABLE:
    with DAG(
        dag_id="enterprise_lakehouse_daily_pipeline",
        default_args=default_args,
        description="Daily Medallion ELT, Data Quality Reconciliation and S3 Backup",
        schedule_interval="0 2 * * *",
        start_date=days_ago(1),
        catchup=False,
        tags=["lakehouse", "clickhouse", "dbt", "reconciliation", "medallion"],
    ) as dag:

        # 1. Ingestion: Extract and land to S3 Parquet & ClickHouse raw.orders_landing
        task_ingest = BashOperator(
            task_id="ingest_batch_orders",
            bash_command="python3 ingestion/sample_ingestion.py",
        )

        # 2. Transformation: Run dbt models (Silver dim_customer, dim_product & Gold fact_sales)
        task_dbt_run = BashOperator(
            task_id="dbt_transform_silver_gold",
            bash_command="docker compose -f compose/docker-compose.dev.yml --profile tools run --rm dbt-runner run --profiles-dir .",
        )

        # 3. Quality Testing: Run dbt assertions and uniqueness tests
        task_dbt_test = BashOperator(
            task_id="dbt_data_quality_tests",
            bash_command="docker compose -f compose/docker-compose.dev.yml --profile tools run --rm dbt-runner test --profiles-dir .",
        )

        # 4. Multi-Layer Reconciliation: Raw vs Silver vs Gold row counts & checksums
        task_reconcile = BashOperator(
            task_id="reconcile_layers_and_score",
            bash_command="python3 -m data_quality.reconciliation",
        )

        # 5. Backup: Snapshot partitions and transfer to S3 backup bucket
        task_backup = BashOperator(
            task_id="clickhouse_s3_backup",
            bash_command="bash scripts/backup_clickhouse.sh",
        )

        # Pipeline Dependency Chain
        task_ingest >> task_dbt_run >> task_dbt_test >> task_reconcile >> task_backup
else:
    # Fallback stub for environments without apache-airflow installed
    dag = None
