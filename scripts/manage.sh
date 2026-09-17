#!/usr/bin/env bash
# ==============================================================================
# Enterprise Data Lakehouse Platform - Developer CLI (Linux / macOS)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

usage() {
  echo "Usage: $0 <command> [args]"
  echo ""
  echo "Commands:"
  echo "  start         Start UAT Core, then the separate Observability stack"
  echo "  stop          Stop the DEV/UAT stack"
  echo "  restart       Restart the DEV/UAT stack"
  echo "  status        Check container status"
  echo "  datasources-start Start PostgreSQL, MySQL, SQL Server, and MongoDB"
  echo "  datasources-stop  Stop the UAT Data Sources stack"
  echo "  ingest        Generate and ingest synthetic orders into ClickHouse and S3"
  echo "  dbt-run       Execute dbt transformations (Bronze -> Silver -> Gold)"
  echo "  dbt-test      Run dbt data quality tests"
  echo "  smoke-test    Run automated end-to-end service health checks"
  echo "  benchmark     Run ClickHouse analytical query performance benchmark"
  echo "  reconcile     Run automated Data Quality reconciliation engine"
  echo "  api-start     Start the Serving REST API microservice (FastAPI)"
  echo "  ai-query      Run governed AI Text-to-SQL query assistant"
  echo "  run-pipeline  Execute automated master Lakehouse pipeline (M06)"
  echo "  streaming-start  Start Redpanda & Console real-time streaming stack (M02)"
  echo "  streaming-stop   Stop Redpanda streaming stack"
  echo "  stream-produce   Simulate real-time streaming event producer"
  echo "  generate-catalog Generate Enterprise Data Catalog & Mermaid Lineage (M08)"
  echo "  stress-test      Run multi-threaded analytical concurrency stress test (M09)"
  echo "  contract-validate Validate data against Open Data Contract (M08)"
  echo "  finops-report    Analyze ClickHouse query cost & workload allocation"
  echo "  vector-demo      Run ClickHouse vector semantic search demo (M12)"
  echo "  anomaly-detect   Run statistical Data Quality anomaly detection (M05)"
  echo "  triage           Run ClickHouse incident diagnostic & runbook triage (M09/M12)"
  echo "  policy-lint      Lint codebase against AGENTS.md engineering policy"
  echo "  master-test      Run 12-module Master End-to-End Acceptance Suite"
  echo "  backup        Run automated ClickHouse S3 backup"
  echo "  restore-drill Run non-destructive restore drill against a backup ID"
  echo "  validate      Validate Compose files, XML configs, and check for secrets"
  exit 1
}

if [ $# -lt 1 ]; then
  usage
fi

COMMAND="$1"
shift || true

case "${COMMAND}" in
  start)
    echo "Starting DEV/UAT stack..."
    if [ ! -f .env ]; then
      echo "Copying .env.example to .env..."
      cp .env.example .env
    fi
    docker compose -f compose/docker-compose.dev.yml up -d
    docker compose -f compose/docker-compose.observability.yml up -d
    echo "Stack started successfully."
    echo "ClickHouse: http://localhost:${CLICKHOUSE_PORT_HTTP:-18123} | Grafana: http://localhost:${GRAFANA_PORT:-13000} | MinIO: http://localhost:${MINIO_CONSOLE_PORT:-19091}"
    ;;
  stop)
    echo "Stopping DEV/UAT stack..."
    docker compose -f compose/docker-compose.observability.yml down
    docker compose -f compose/docker-compose.dev.yml down
    ;;
  restart)
    echo "Restarting DEV/UAT stack..."
    docker compose -f compose/docker-compose.dev.yml restart
    ;;
  status)
    docker compose -f compose/docker-compose.dev.yml ps
    docker compose -f compose/docker-compose.observability.yml ps
    ;;
  datasources-start)
    echo "Starting UAT Data Sources stack..."
    docker compose -f compose/docker-compose.datasources.yml up -d
    ;;
  datasources-stop)
    echo "Stopping UAT Data Sources stack..."
    docker compose -f compose/docker-compose.datasources.yml down
    ;;
  ingest)
    echo "Running synthetic data ingestion..."
    python3 ingestion/sample_ingestion.py
    ;;
  dbt-run)
    echo "Running dbt transformations..."
    docker compose -f compose/docker-compose.dev.yml --profile tools run --rm dbt-runner run --profiles-dir .
    ;;
  dbt-test)
    echo "Running dbt data quality tests..."
    docker compose -f compose/docker-compose.dev.yml --profile tools run --rm dbt-runner test --profiles-dir .
    ;;
  smoke-test)
    python3 scripts/smoke_test.py
    ;;
  benchmark)
    python3 scripts/benchmark_queries.py
    ;;
  reconcile)
    echo "Running Data Quality & Reconciliation Engine..."
    python3 -m data_quality.reconciliation
    ;;
  api-start)
    echo "Starting Serving REST API microservice..."
    docker compose -f compose/docker-compose.dev.yml --profile api up -d serving-api
    echo "API running at: http://localhost:${SERVING_API_PORT:-18000}/docs"
    ;;
  ai-query)
    QUERY="${1:-แสดงยอดขายรายวัน 14 วันล่าสุด}"
    python3 -m ai_assistant.text_to_sql "${QUERY}"
    ;;
  run-pipeline)
    echo "Executing Master Lakehouse Pipeline..."
    python3 orchestration/pipeline_orchestrator.py "$@"
    ;;
  streaming-start)
    echo "Starting Redpanda & Console Streaming Stack..."
    docker compose -f compose/docker-compose.streaming.yml up -d
    echo "Streaming Stack active!"
    echo "Kafka Broker: localhost:${REDPANDA_PORT_KAFKA:-19092} | Redpanda Console: http://localhost:${REDPANDA_CONSOLE_PORT:-18088}"
    ;;
  streaming-stop)
    echo "Stopping Streaming Stack..."
    docker compose -f compose/docker-compose.streaming.yml down
    ;;
  stream-produce)
    echo "Producing real-time streaming events..."
    python3 streaming/kafka_producer_sim.py "$@"
    ;;
  generate-catalog)
    echo "Generating Enterprise Data Catalog & Mermaid Lineage..."
    python3 scripts/generate_catalog.py
    ;;
  stress-test)
    echo "Running analytical concurrency stress test..."
    python3 scripts/stress_test.py "$@"
    ;;
  contract-validate)
    echo "Validating dataset against Open Data Contract..."
    python3 governance/validate_contract.py "$@"
    ;;
  finops-report)
    echo "Analyzing query compute cost & resource quotas..."
    python3 finops/query_cost_analyzer.py "$@"
    ;;
  vector-demo)
    echo "Running ClickHouse vector semantic search demo..."
    QUERY="${1:-how to solve too many parts and replication lag}"
    python3 ai_assistant/vector_search.py "${QUERY}"
    ;;
  anomaly-detect)
    echo "Running Data Quality Anomaly Detector..."
    python3 data_quality/anomaly_detector.py "$@"
    ;;
  triage)
    echo "Running ClickHouse Incident Triage Diagnostic..."
    python3 ai_assistant/incident_triage.py "$@"
    ;;
  policy-lint)
    echo "Linting codebase against AGENTS.md engineering policy..."
    python3 governance/policy_linter.py
    ;;
  master-test)
    echo "Executing Master End-to-End Acceptance Suite across 12 modules..."
    python3 scripts/master_e2e_test.py
    ;;
  backup)
    bash scripts/backup_clickhouse.sh
    ;;
  restore-drill)
    if [ $# -lt 1 ]; then
      echo "Usage: $0 restore-drill <backup_id>"
      exit 1
    fi
    bash scripts/restore_test.sh "$1"
    ;;
  validate)
    bash scripts/validate_stack.sh
    ;;
  *)
    usage
    ;;
esac
