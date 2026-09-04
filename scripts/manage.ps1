# ==============================================================================
# Enterprise Data Lakehouse Platform - Developer CLI (Windows PowerShell)
# ==============================================================================
param (
    [Parameter(Position=0, Mandatory=$false)]
    [string]$Command = "help",

    [Parameter(Position=1, Mandatory=$false, ValueFromRemainingArguments=$true)]
    [string[]]$ExtraArgs
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
Set-Location $RootDir

$Arg1 = if ($ExtraArgs -and $ExtraArgs.Count -gt 0) { $ExtraArgs[0] } else { "" }

function Show-Help {
    Write-Host "Usage: .\scripts\manage.ps1 <command> [args]" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  start         Start the DEV/UAT stack (ClickHouse, MinIO, Portainer, Prometheus, Grafana)"
    Write-Host "  stop          Stop the DEV/UAT stack"
    Write-Host "  restart       Restart the DEV/UAT stack"
    Write-Host "  status        Check container status"
    Write-Host "  ingest        Generate and ingest synthetic orders into ClickHouse and S3"
    Write-Host "  dbt-run       Execute dbt transformations (Bronze -> Silver -> Gold)"
    Write-Host "  dbt-test      Run dbt data quality tests"
    Write-Host "  smoke-test    Run automated end-to-end service health checks"
    Write-Host "  benchmark     Run ClickHouse analytical query performance benchmark"
    Write-Host "  reconcile     Run automated Data Quality reconciliation engine"
    Write-Host "  api-start        Start the Serving REST API microservice (FastAPI)"
    Write-Host "  ai-query         Run governed AI Text-to-SQL query assistant"
    Write-Host "  run-pipeline     Execute automated master Lakehouse pipeline (M06)"
    Write-Host "  streaming-start  Start Redpanda & Console real-time streaming stack (M02)"
    Write-Host "  streaming-stop   Stop Redpanda streaming stack"
    Write-Host "  stream-produce   Simulate real-time streaming event producer"
    Write-Host "  generate-catalog Generate Enterprise Data Catalog & Mermaid Lineage (M08)"
    Write-Host "  stress-test      Run multi-threaded analytical concurrency stress test (M09)"
    Write-Host "  contract-validate Validate data against Open Data Contract (M08)"
    Write-Host "  finops-report    Analyze ClickHouse query cost & workload allocation"
    Write-Host "  vector-demo      Run ClickHouse vector semantic search demo (M12)"
    Write-Host "  anomaly-detect   Run statistical Data Quality anomaly detection (M05)"
    Write-Host "  triage           Run ClickHouse incident diagnostic & runbook triage (M09/M12)"
    Write-Host "  policy-lint      Lint codebase against AGENTS.md engineering policy"
    Write-Host "  master-test      Run 12-module Master End-to-End Acceptance Suite"
    Write-Host "  backup           Run automated ClickHouse S3 backup"
    Write-Host "  restore-drill    Run non-destructive restore drill against a backup ID"
    Write-Host "  validate         Validate Compose files, XML configs, and check for secrets"
}

switch ($Command.ToLower()) {
    "start" {
        Write-Host "Starting DEV/UAT stack..." -ForegroundColor Green
        if (-not (Test-Path ".env")) {
            Write-Host "Copying .env.example to .env..."
            Copy-Item ".env.example" ".env"
        }
        docker compose -f compose/docker-compose.dev.yml up -d
        Write-Host "Stack started successfully!" -ForegroundColor Green
        Write-Host "ClickHouse: http://localhost:8123 | Grafana: http://localhost:3000 | MinIO: http://localhost:9001"
    }
    "stop" {
        Write-Host "Stopping DEV/UAT stack..." -ForegroundColor Yellow
        docker compose -f compose/docker-compose.dev.yml down
    }
    "restart" {
        Write-Host "Restarting DEV/UAT stack..." -ForegroundColor Yellow
        docker compose -f compose/docker-compose.dev.yml restart
    }
    "status" {
        docker compose -f compose/docker-compose.dev.yml ps
    }
    "ingest" {
        Write-Host "Running synthetic data ingestion..." -ForegroundColor Cyan
        python ingestion/sample_ingestion.py
    }
    "dbt-run" {
        Write-Host "Running dbt transformations..." -ForegroundColor Cyan
        docker compose -f compose/docker-compose.dev.yml --profile tools run --rm dbt-runner run --profiles-dir .
    }
    "dbt-test" {
        Write-Host "Running dbt data quality tests..." -ForegroundColor Cyan
        docker compose -f compose/docker-compose.dev.yml --profile tools run --rm dbt-runner test --profiles-dir .
    }
    "smoke-test" {
        python scripts/smoke_test.py
    }
    "benchmark" {
        python scripts/benchmark_queries.py
    }
    "reconcile" {
        Write-Host "Running Data Quality & Reconciliation Engine..." -ForegroundColor Cyan
        python -m data_quality.reconciliation
    }
    "api-start" {
        Write-Host "Starting Serving REST API microservice..." -ForegroundColor Cyan
        docker compose -f compose/docker-compose.dev.yml --profile api up -d serving-api
        Write-Host "API running at: http://localhost:8000/docs" -ForegroundColor Green
    }
    "ai-query" {
        $q = "daily sales trend"
        if (-not [string]::IsNullOrWhiteSpace($Arg1)) {
            $q = $Arg1
        }
        python -m ai_assistant.text_to_sql $q
    }
    "run-pipeline" {
        Write-Host "Executing Master Lakehouse Pipeline..." -ForegroundColor Cyan
        $argsList = @()
        if ($Arg1 -eq "--dry-run") {
            $argsList += "--dry-run"
        }
        python orchestration/pipeline_orchestrator.py @argsList
    }
    "streaming-start" {
        Write-Host "Starting Redpanda & Console Streaming Stack..." -ForegroundColor Cyan
        docker compose -f compose/docker-compose.streaming.yml up -d
        Write-Host "Streaming Stack active!" -ForegroundColor Green
        Write-Host "Kafka Broker: localhost:9092 | Redpanda Console: http://localhost:8088"
    }
    "streaming-stop" {
        Write-Host "Stopping Streaming Stack..." -ForegroundColor Yellow
        docker compose -f compose/docker-compose.streaming.yml down
    }
    "stream-produce" {
        Write-Host "Producing real-time streaming events..." -ForegroundColor Cyan
        python streaming/kafka_producer_sim.py
    }
    "generate-catalog" {
        Write-Host "Generating Enterprise Data Catalog & Mermaid Lineage..." -ForegroundColor Cyan
        python scripts/generate_catalog.py
    }
    "stress-test" {
        Write-Host "Running analytical concurrency stress test..." -ForegroundColor Cyan
        $c = 10
        $extra = @()
        if ($ExtraArgs) {
            foreach ($a in $ExtraArgs) {
                if ($a -match "^\d+$") {
                    $c = [int]$a
                } else {
                    $extra += $a
                }
            }
        }
        python scripts/stress_test.py --concurrency $c @extra
    }
    "contract-validate" {
        Write-Host "Validating dataset against Open Data Contract..." -ForegroundColor Cyan
        $extra = @()
        if ($ExtraArgs) {
            $extra = $ExtraArgs
        }
        python governance/validate_contract.py @extra
    }
    "finops-report" {
        Write-Host "Analyzing query compute cost & resource quotas..." -ForegroundColor Cyan
        $extra = @()
        if ($ExtraArgs) {
            $extra = $ExtraArgs
        }
        python finops/query_cost_analyzer.py @extra
    }
    "vector-demo" {
        Write-Host "Running ClickHouse vector semantic search demo..." -ForegroundColor Cyan
        $q = "how to solve too many parts and replication lag"
        if (-not [string]::IsNullOrWhiteSpace($Arg1)) {
            $q = $Arg1
        }
        python ai_assistant/vector_search.py $q
    }
    "anomaly-detect" {
        Write-Host "Running Data Quality Anomaly Detector..." -ForegroundColor Cyan
        $extra = @()
        if ($ExtraArgs) {
            $extra = $ExtraArgs
        }
        python data_quality/anomaly_detector.py @extra
    }
    "triage" {
        Write-Host "Running ClickHouse Incident Triage Diagnostic..." -ForegroundColor Cyan
        $extra = @()
        if ($ExtraArgs) {
            $extra = $ExtraArgs
        }
        python ai_assistant/incident_triage.py @extra
    }
    "policy-lint" {
        Write-Host "Linting codebase against AGENTS.md engineering policy..." -ForegroundColor Cyan
        python governance/policy_linter.py
    }
    "master-test" {
        Write-Host "Executing Master End-to-End Acceptance Suite across 12 modules..." -ForegroundColor Cyan
        python scripts/master_e2e_test.py
    }
    "backup" {
        bash scripts/backup_clickhouse.sh
    }
    "restore-drill" {
        if ([string]::IsNullOrWhiteSpace($Arg1)) {
            Write-Error "Please specify backup ID. Example: .\scripts\manage.ps1 restore-drill 20260903_120000"
        }
        bash scripts/restore_test.sh $Arg1
    }
    "validate" {
        Write-Host "Validating Docker Compose configs..." -ForegroundColor Cyan
        docker compose -f compose/docker-compose.dev.yml config > $null
        docker compose -f compose/docker-compose.prod-node1.yml config > $null
        docker compose -f compose/docker-compose.prod-node2.yml config > $null
        docker compose -f compose/docker-compose.prod-keeper3.yml config > $null
        docker compose -f compose/docker-compose.observability.yml config > $null
        docker compose -f compose/docker-compose.streaming.yml config > $null
        Write-Host "All Compose files valid!" -ForegroundColor Green

        Write-Host "Validating XML configurations..." -ForegroundColor Cyan
        python -c "import xml.etree.ElementTree as ET, glob, sys; [ET.parse(f) for f in glob.glob('clickhouse/**/*.xml', recursive=True)]; print('All XML configurations valid!')"
    }
    default {
        Show-Help
    }
}
