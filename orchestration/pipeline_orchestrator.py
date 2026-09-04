#!/usr/bin/env python3
"""
=============================================================================
Enterprise Data Lakehouse Platform - Master Pipeline Orchestrator (M06)
=============================================================================
Orchestrates the complete Lakehouse data lifecycle:
1. INGESTION       : Ingest batch data into S3 and ClickHouse raw tables.
2. TRANSFORMATION  : Run dbt models (Bronze -> Silver -> Gold).
3. TESTING         : Execute dbt data quality assertion tests.
4. RECONCILIATION  : Multi-layer row count and checksum reconciliation.
5. BACKUP          : Automated non-blocking ClickHouse S3 backup.
6. NOTIFICATION    : Webhook alerting (Slack/Teams/Discord/Custom HTTP).

Governed by AGENTS.md:
- Zero credentials in execution logs.
- Deterministic error tracking and audit records.
"""

import os
import sys
import json
import time
import argparse
import logging
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Orchestrator] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("LakehouseOrchestrator")


class PipelineStep:
    def __init__(
        self,
        name: str,
        command: List[str],
        critical: bool = True,
        max_retries: int = 2,
        retry_delay_sec: int = 5,
        description: str = ""
    ):
        self.name = name
        self.command = command
        self.critical = critical
        self.max_retries = max_retries
        self.retry_delay_sec = retry_delay_sec
        self.description = description
        self.status = "PENDING"
        self.duration_sec = 0.0
        self.error_message = ""


class LakehousePipeline:
    def __init__(
        self,
        dry_run: bool = False,
        skip_backup: bool = False,
        webhook_url: Optional[str] = None,
        continue_on_error: bool = False
    ):
        self.dry_run = dry_run
        self.skip_backup = skip_backup
        self.webhook_url = webhook_url or os.environ.get("PIPELINE_WEBHOOK_URL")
        self.continue_on_error = continue_on_error
        self.run_id = datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")
        self.steps: List[PipelineStep] = []
        self._build_steps()

    def _build_steps(self):
        # 1. Ingestion
        self.steps.append(
            PipelineStep(
                name="INGESTION",
                command=[sys.executable, "ingestion/sample_ingestion.py"],
                critical=True,
                max_retries=2,
                description="Ingest batch records into S3 Parquet landing & ClickHouse raw tables"
            )
        )

        # 2. dbt Transformation (Silver & Gold)
        dbt_cmd = ["docker", "compose", "-f", "compose/docker-compose.dev.yml", "--profile", "tools", "run", "--rm", "dbt-runner", "run", "--profiles-dir", "."]
        self.steps.append(
            PipelineStep(
                name="TRANSFORMATION",
                command=dbt_cmd,
                critical=True,
                max_retries=1,
                description="Execute dbt models: raw.orders_landing -> core.dim_* & mart.fact_sales"
            )
        )

        # 3. dbt Data Quality Tests
        dbt_test_cmd = ["docker", "compose", "-f", "compose/docker-compose.dev.yml", "--profile", "tools", "run", "--rm", "dbt-runner", "test", "--profiles-dir", "."]
        self.steps.append(
            PipelineStep(
                name="DATA_TESTS",
                command=dbt_test_cmd,
                critical=True,
                max_retries=1,
                description="Assert schema integrity, positive values, and uniqueness in dbt models"
            )
        )

        # 4. Multi-Layer Data Reconciliation
        self.steps.append(
            PipelineStep(
                name="RECONCILIATION",
                command=[sys.executable, "-m", "data_quality.reconciliation"],
                critical=False,
                max_retries=1,
                description="Cross-layer row count reconciliation and Data Quality Score calculation"
            )
        )

        # 5. Backup (Optional)
        if not self.skip_backup:
            # Determine shell runner based on OS
            is_windows = sys.platform.startswith("win")
            backup_cmd = ["bash", "scripts/backup_clickhouse.sh"] if not is_windows else ["powershell", "-ExecutionPolicy", "Bypass", "-File", "scripts/manage.ps1", "backup"]
            self.steps.append(
                PipelineStep(
                    name="BACKUP",
                    command=backup_cmd,
                    critical=False,
                    max_retries=1,
                    description="Trigger ClickHouse partition snapshot to S3 backup bucket"
                )
            )

    def execute_step(self, step: PipelineStep) -> bool:
        logger.info(f"=== Starting Step: {step.name} ===")
        logger.info(f"Description: {step.description}")

        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute: {' '.join(step.command)}")
            step.status = "SUCCESS (DRY_RUN)"
            step.duration_sec = 0.05
            return True

        attempt = 0
        while attempt <= step.max_retries:
            attempt += 1
            logger.info(f"Executing attempt {attempt}/{step.max_retries + 1}...")
            start_time = time.time()
            try:
                result = subprocess.run(
                    step.command,
                    capture_output=True,
                    text=True,
                    check=False
                )
                duration = time.time() - start_time
                step.duration_sec = round(duration, 2)

                if result.returncode == 0:
                    step.status = "SUCCESS"
                    logger.info(f"Step {step.name} completed successfully in {step.duration_sec}s.")
                    if result.stdout.strip():
                        # Print last 5 lines of stdout for brevity
                        last_lines = "\n".join(result.stdout.strip().splitlines()[-5:])
                        logger.info(f"Output summary:\n{last_lines}")
                    return True
                else:
                    step.error_message = result.stderr.strip() or result.stdout.strip()
                    logger.warning(f"Step {step.name} attempt {attempt} failed with exit code {result.returncode}.")
                    if attempt <= step.max_retries:
                        logger.info(f"Waiting {step.retry_delay_sec}s before retry...")
                        time.sleep(step.retry_delay_sec)
            except Exception as e:
                step.duration_sec = round(time.time() - start_time, 2)
                step.error_message = str(e)
                logger.error(f"Execution exception on step {step.name}: {e}")
                if attempt <= step.max_retries:
                    time.sleep(step.retry_delay_sec)

        step.status = "FAILED"
        return False

    def run(self) -> Dict[str, Any]:
        overall_start = time.time()
        logger.info(f"============================================================")
        logger.info(f"Starting Lakehouse Pipeline Run: {self.run_id}")
        logger.info(f"Dry Run: {self.dry_run} | Skip Backup: {self.skip_backup}")
        logger.info(f"============================================================")

        pipeline_status = "SUCCESS"
        for step in self.steps:
            success = self.execute_step(step)
            if not success:
                if step.critical and not self.continue_on_error:
                    pipeline_status = "FAILED"
                    logger.error(f"Critical step {step.name} failed. Halting pipeline execution.")
                    break
                else:
                    pipeline_status = "PARTIAL_SUCCESS"
                    logger.warning(f"Non-critical step {step.name} failed. Continuing pipeline.")

        total_duration = round(time.time() - overall_start, 2)
        summary = {
            "run_id": self.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": pipeline_status,
            "total_duration_sec": total_duration,
            "dry_run": self.dry_run,
            "steps": [
                {
                    "name": s.name,
                    "status": s.status,
                    "duration_sec": s.duration_sec,
                    "description": s.description,
                    "error": s.error_message[:200] if s.error_message else None
                }
                for s in self.steps
            ]
        }

        self._record_audit_log(summary)
        self._send_notification(summary)
        self._print_summary(summary)
        return summary

    def _record_audit_log(self, summary: Dict[str, Any]):
        log_dir = os.path.join(os.path.dirname(__file__), "runs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"{self.run_id}.json")
        try:
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            logger.info(f"Audit log saved to: {log_file}")
        except Exception as e:
            logger.error(f"Failed to write pipeline audit log: {e}")

    def _send_notification(self, summary: Dict[str, Any]):
        if not self.webhook_url:
            return
        logger.info(f"Sending webhook notification to {self.webhook_url}...")
        try:
            import urllib.request
            payload = {
                "text": f"Lakehouse Pipeline Run: {summary['run_id']} - Status: {summary['status']}",
                "run_id": summary["run_id"],
                "status": summary["status"],
                "duration_sec": summary["total_duration_sec"],
                "timestamp": summary["timestamp"]
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                logger.info(f"Webhook notification delivered (HTTP {resp.status})")
        except Exception as e:
            logger.warning(f"Failed to deliver webhook notification: {e}")

    def _print_summary(self, summary: Dict[str, Any]):
        print("\n" + "=" * 68)
        print(f" PIPELINE EXECUTION SUMMARY: {summary['run_id']}")
        print("=" * 68)
        print(f" Status         : {summary['status']}")
        print(f" Total Duration : {summary['total_duration_sec']}s")
        print("-" * 68)
        print(f"{'STEP':<18} | {'STATUS':<20} | {'DURATION':<10}")
        print("-" * 68)
        for s in summary["steps"]:
            print(f"{s['name']:<18} | {s['status']:<20} | {s['duration_sec']}s")
        print("=" * 68 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Enterprise Data Lakehouse Pipeline Orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without running external commands")
    parser.add_argument("--skip-backup", action="store_true", help="Skip the final S3 backup step")
    parser.add_argument("--continue-on-error", action="store_true", help="Do not halt on critical step failure")
    parser.add_argument("--webhook-url", type=str, default=None, help="Optional notification webhook URL")

    args = parser.parse_args()
    pipeline = LakehousePipeline(
        dry_run=args.dry_run,
        skip_backup=args.skip_backup,
        webhook_url=args.webhook_url,
        continue_on_error=args.continue_on_error
    )
    result = pipeline.run()
    if result["status"] == "FAILED":
        sys.exit(1)


if __name__ == "__main__":
    main()
