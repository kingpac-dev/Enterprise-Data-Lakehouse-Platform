"""Build a Superset 6.1 dashboard import bundle without credentials or customer data.

The asset UUIDs are stable. Import deliberately happens only on operator request:
the Superset CLI replaces the layout of an existing dashboard with the same UUID.
"""

import json
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

VERSION = "1.0.0"
DATABASE_UUID = "3600f2f0-6310-4745-b23e-63ad596a3240"
DATASET_UUID = "50f097c4-1bbd-47a3-a0a7-102f85bc16ce"
DASHBOARD_UUID = "7859db96-a892-4c64-970e-46eebda0ca39"

METRICS = {
    "sales_amount": ("Sales amount", "sum(amount)"),
    "source_orders": ("Distinct source-order pairs", "uniqExact(_source_system, order_id)"),
    "customer_ids": ("Distinct customer IDs", "uniqExact(customer_id)"),
    "quantity": ("Quantity", "sum(quantity)"),
}

CHARTS = [
    ("sales", "Sales amount", "sales_amount", "d640ce1e-26d4-4769-9d2f-65d48f7d0f21"),
    ("orders", "Distinct source-order pairs", "source_orders", "de219c73-9baf-4608-b6ed-c68bef178108"),
    ("customers", "Distinct customer IDs", "customer_ids", "2a700b58-fde7-4e98-8792-72e7ef92edc0"),
    ("quantity", "Quantity", "quantity", "fe0961aa-2d82-4d58-84f9-a56fd7eba83f"),
    ("trend", "Daily sales by branch", "sales_amount", "47f668f3-7f1c-40bc-a4ea-10a98c3a4a5d"),
]


def build_assets() -> dict[str, dict]:
    columns = [
        ("sale_date", "Date", True),
        ("branch_id", "UInt32", False),
        ("order_id", "UInt64", False),
        ("customer_id", "UInt64", False),
        ("quantity", "Decimal(18, 3)", False),
        ("amount", "Decimal(18, 2)", False),
        ("_source_system", "LowCardinality(String)", False),
    ]
    assets = {
        "metadata.yaml": {"version": VERSION, "type": "Dashboard"},
        "databases/kingpac_clickhouse.yaml": {
            "database_name": "KingPac ClickHouse UAT",
            # Deliberately no password. An administrator sets the real URI in the UI.
            "sqlalchemy_uri": "clickhousedb://bi_user@lakehouse-clickhouse-dev:8123/mart",
            "uuid": DATABASE_UUID,
            "version": VERSION,
            "expose_in_sqllab": False,
            "allow_run_async": False,
            "allow_ctas": False,
            "allow_cvas": False,
            "allow_dml": False,
            "allow_file_upload": False,
            "extra": {},
        },
        "datasets/kingpac_fact_sales.yaml": {
            "table_name": "fact_sales",
            "schema": "mart",
            "main_dttm_col": "sale_date",
            "description": "UAT demonstration; reconcile and approve definitions before business use.",
            "uuid": DATASET_UUID,
            "database_uuid": DATABASE_UUID,
            "version": VERSION,
            "columns": [
                {"column_name": name, "type": kind, "is_dttm": temporal,
                 "groupby": True, "filterable": True, "is_active": True}
                for name, kind, temporal in columns
            ],
            "metrics": [
                {"metric_name": name, "verbose_name": title, "expression": expression}
                for name, (title, expression) in METRICS.items()
            ],
        },
    }

    position = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"id": "ROOT_ID", "type": "ROOT", "children": ["GRID_ID"]},
        "GRID_ID": {"id": "GRID_ID", "type": "GRID", "parents": ["ROOT_ID"],
                    "children": ["ROW-KPIS", "ROW-TREND"]},
        "HEADER_ID": {"id": "HEADER_ID", "type": "HEADER",
                      "meta": {"text": "KingPac Sales Overview — UAT"}},
        "ROW-KPIS": {"id": "ROW-KPIS", "type": "ROW", "parents": ["ROOT_ID", "GRID_ID"],
                     "meta": {"background": "BACKGROUND_TRANSPARENT"},
                     "children": [f"CHART-{name}" for name, _, _, _ in CHARTS[:4]]},
        "ROW-TREND": {"id": "ROW-TREND", "type": "ROW", "parents": ["ROOT_ID", "GRID_ID"],
                      "meta": {"background": "BACKGROUND_TRANSPARENT"}, "children": ["CHART-trend"]},
    }

    for index, (name, title, metric, chart_uuid) in enumerate(CHARTS, start=1):
        trend = name == "trend"
        viz_type = "echarts_timeseries_bar" if trend else "big_number_total"
        params = {
            "viz_type": viz_type,
            "datasource": "0__table",  # rewritten to imported dataset ID by Superset
            "adhoc_filters": [{"clause": "WHERE", "comparator": "Last 30 days",
                               "expressionType": "SIMPLE", "operator": "TEMPORAL_RANGE",
                               "subject": "sale_date"}],
            "time_range": "Last 30 days",
            "granularity_sqla": "sale_date",
            "extra_form_data": {},
        }
        if trend:
            params.update({"metrics": [metric], "groupby": ["branch_id"], "x_axis": "sale_date",
                           "time_grain_sqla": "P1D", "row_limit": 1000,
                           "show_legend": True, "color_scheme": "supersetColors",
                           "orientation": "vertical", "stack": "Stack"})
        else:
            params.update({"metric": metric, "header_font_size": 0.4,
                           "subheader_font_size": 0.15, "y_axis_format": ",.2f" if name in ("sales", "quantity") else ",d"})
        assets[f"charts/{name}.yaml"] = {
            "slice_name": title, "description": "UAT only; metric requires owner validation.",
            "viz_type": viz_type, "params": params, "query_context": None,
            "dataset_uuid": DATASET_UUID, "uuid": chart_uuid, "version": VERSION,
        }
        row = "ROW-TREND" if trend else "ROW-KPIS"
        position[f"CHART-{name}"] = {
            "id": f"CHART-{name}", "type": "CHART", "children": [],
            "parents": ["ROOT_ID", "GRID_ID", row],
            "meta": {"chartId": index, "uuid": chart_uuid, "sliceName": title,
                     "width": 12 if trend else 3, "height": 50 if trend else 20},
        }

    assets["dashboards/sales_overview.yaml"] = {
        "dashboard_title": "KingPac Sales Overview — UAT",
        "description": "Synthetic or masked data only; KPI definitions are not certified.",
        "slug": "kingpac-sales-uat", "uuid": DASHBOARD_UUID, "version": VERSION,
        "published": False, "position": position,
        "metadata": {
            "color_scheme": "supersetColors",
            "native_filter_configuration": [
                {"id": "NATIVE_FILTER-time", "name": "Time range", "filterType": "filter_time",
                 "type": "NATIVE_FILTER", "targets": [{}], "cascadeParentIds": [],
                 "controlValues": {"enableEmptyFilter": False},
                 "defaultDataMask": {"extraFormData": {}, "filterState": {}, "ownState": {}},
                 "scope": {"rootPath": ["ROOT_ID"], "excluded": []}},
                {"id": "NATIVE_FILTER-branch", "name": "Branch", "filterType": "filter_select",
                 "type": "NATIVE_FILTER", "targets": [{"datasetUuid": DATASET_UUID,
                                                           "column": {"name": "branch_id"}}],
                 "cascadeParentIds": [], "controlValues": {"multiSelect": True,
                 "enableEmptyFilter": False, "searchAllOptions": False, "inverseSelection": False},
                 "defaultDataMask": {"extraFormData": {}, "filterState": {}, "ownState": {}},
                 "scope": {"rootPath": ["ROOT_ID"], "excluded": []}},
            ],
        },
    }
    return assets


def write_bundle(destination: Path) -> None:
    with ZipFile(destination, "w", compression=ZIP_DEFLATED) as bundle:
        for name, content in build_assets().items():
            # JSON is a subset of YAML 1.2, accepted by Superset's YAML loader.
            bundle.writestr(f"kingpac_insight/{name}", json.dumps(content, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python build_demo_bundle.py <output.zip>")
    write_bundle(Path(sys.argv[1]))
    print("UAT demo bundle created; configure the ClickHouse connection after import.")
