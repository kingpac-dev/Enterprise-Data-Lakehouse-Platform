import importlib.util
import json
import os
import runpy
import sys
import tempfile
import types
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("demo_bundle", ROOT / "build_demo_bundle.py")
bundle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bundle)


class DemoBundleTests(unittest.TestCase):
    def test_bundle_references_are_consistent_and_no_credentials_are_embedded(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "demo.zip"
            bundle.write_bundle(path)
            with ZipFile(path) as archive:
                contents = {name.split("/", 1)[1]: json.loads(archive.read(name)) for name in archive.namelist()}
        db = contents["databases/kingpac_clickhouse.yaml"]
        dataset = contents["datasets/kingpac_fact_sales.yaml"]
        dashboard = contents["dashboards/sales_overview.yaml"]
        charts = [value for name, value in contents.items() if name.startswith("charts/")]
        self.assertEqual(db["uuid"], dataset["database_uuid"])
        self.assertEqual({chart["dataset_uuid"] for chart in charts}, {dataset["uuid"]})
        positions = [v for v in dashboard["position"].values() if isinstance(v, dict) and v.get("type") == "CHART"]
        self.assertEqual({p["meta"]["uuid"] for p in positions}, {c["uuid"] for c in charts})
        self.assertNotIn(":password@", db["sqlalchemy_uri"])
        self.assertFalse(db["expose_in_sqllab"])
        self.assertFalse(db["allow_dml"])
        self.assertFalse(db["allow_file_upload"])

    def test_distinct_metrics_are_computed_from_fact_rows(self):
        dataset = bundle.build_assets()["datasets/kingpac_fact_sales.yaml"]
        metrics = {m["metric_name"]: m["expression"] for m in dataset["metrics"]}
        self.assertEqual(dataset["table_name"], "fact_sales")
        self.assertEqual(metrics["source_orders"], "uniqExact(_source_system, order_id)")
        self.assertEqual(metrics["customer_ids"], "uniqExact(customer_id)")
        self.assertNotIn("unique_customers", " ".join(metrics.values()))


class ConfigTests(unittest.TestCase):
    def test_metadata_credentials_are_url_encoded_and_https_is_opt_in(self):
        env = {"SUPERSET_SECRET_KEY": "test-key-for-configuration-only-1234567890", "INSIGHT_POSTGRES_USER": "user@name",
               "INSIGHT_POSTGRES_PASSWORD": "test:/@pass", "INSIGHT_POSTGRES_DB": "db/name",
               "INSIGHT_HTTPS_ENABLED": "true"}
        with patch.dict(os.environ, env, clear=True):
            config = runpy.run_path(str(ROOT / "superset_config.py"))
        self.assertEqual(config["SQLALCHEMY_DATABASE_URI"],
                         "postgresql+psycopg2://user%40name:test%3A%2F%40pass@metadata:5432/db%2Fname")
        self.assertTrue(config["SESSION_COOKIE_SECURE"])
        self.assertTrue(config["TALISMAN_CONFIG"]["session_cookie_secure"])
        self.assertFalse(config["FEATURE_FLAGS"]["ENABLE_TEMPLATE_PROCESSING"])

    def test_missing_secret_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(RuntimeError, "SUPERSET_SECRET_KEY"):
            runpy.run_path(str(ROOT / "superset_config.py"))

    def test_short_secret_fails_closed(self):
        with patch.dict(os.environ, {"SUPERSET_SECRET_KEY": "short"}, clear=True), \
                self.assertRaisesRegex(RuntimeError, "at least 32"):
            runpy.run_path(str(ROOT / "superset_config.py"))


class AdminBootstrapTests(unittest.TestCase):
    def test_existing_admin_is_not_changed_and_needs_no_password(self):
        manager = types.SimpleNamespace(find_user=lambda username: object())
        app_module = types.ModuleType("superset.app")
        app_module.create_app = lambda: types.SimpleNamespace(app_context=nullcontext)
        package = types.ModuleType("superset")
        package.__path__ = []
        package.security_manager = manager
        env = {"INSIGHT_ADMIN_USERNAME": "uat-admin", "INSIGHT_ADMIN_EMAIL": "admin@example.invalid"}
        with patch.dict(sys.modules, {"superset": package, "superset.app": app_module}), \
                patch.dict(os.environ, env, clear=True):
            script = runpy.run_path(str(ROOT / "create_admin.py"), run_name="bootstrap_test")
            script["main"]()

    def test_new_admin_requires_a_password(self):
        manager = types.SimpleNamespace(find_user=lambda username: None)
        app_module = types.ModuleType("superset.app")
        app_module.create_app = lambda: types.SimpleNamespace(app_context=nullcontext)
        package = types.ModuleType("superset")
        package.__path__ = []
        package.security_manager = manager
        env = {"INSIGHT_ADMIN_USERNAME": "uat-admin", "INSIGHT_ADMIN_EMAIL": "admin@example.invalid"}
        with patch.dict(sys.modules, {"superset": package, "superset.app": app_module}), \
                patch.dict(os.environ, env, clear=True):
            script = runpy.run_path(str(ROOT / "create_admin.py"), run_name="bootstrap_test")
            with self.assertRaisesRegex(RuntimeError, "INSIGHT_ADMIN_PASSWORD"):
                script["main"]()


if __name__ == "__main__":
    unittest.main()
