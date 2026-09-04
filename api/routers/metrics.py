"""
Metrics & Health Router
=======================
Exposes cluster operational status and Data Quality scores to monitoring consumers.
"""

import os
import sys
from fastapi import APIRouter

# Allow importing from data_quality module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from data_quality.reconciliation import DataReconciliationEngine

router = APIRouter(prefix="/api/v1/metrics", tags=["Platform Metrics"])


@router.get("/data-quality")
def get_data_quality_report():
    """Runs on-demand data quality reconciliation report."""
    engine = DataReconciliationEngine()
    report = engine.run_reconciliation()
    return report


@router.get("/cluster-stats")
def get_cluster_stats():
    """Returns basic query and part statistics."""
    engine = DataReconciliationEngine()
    qps = engine.query("SELECT round(sum(rate(ClickHouseAsyncMetrics_Query[1m])), 2) FROM system.asynchronous_metrics")
    active_parts = engine.query("SELECT count() FROM system.parts WHERE active = 1")
    return {
        "status": "online",
        "active_parts": int(active_parts) if active_parts.isdigit() else active_parts,
        "query_signal": qps,
    }
