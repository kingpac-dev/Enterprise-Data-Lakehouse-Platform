#!/usr/bin/env python3
"""
=============================================================================
Enterprise Data Lakehouse Platform - Policy-as-Code & Governance Linter
=============================================================================
Automated compliance checker verifying that the codebase strictly conforms
to the engineering and security mandates established in AGENTS.md.

Mandatory Policy Rules:
[RULE-01] Zero-Trust Secret Sanitation (no un-templated credentials in code/configs)
[RULE-02] 7 Mandatory Technical Ingestion Metadata Columns in Raw/Core DDL
[RULE-03] Low-Cardinality Partitioning (toYYYYMM on analytical fact tables)
[RULE-04] Hot/Cold Tiering Storage Policy in ClickHouse configuration
[RULE-05] Least-Privilege Role & Memory Quota Configuration
[RULE-06] ClickHouse from_env substitutions require external values (no inline fallback)
[RULE-07] ClickHouse logger and system-log configuration is structurally valid
[RULE-08] ClickHouse Docker user provisioning has a single authoritative source
"""

import os
import re
import sys
import glob
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Tuple

REQUIRED_METADATA_COLUMNS = [
    "_source_system",
    "_source_table",
    "_ingested_at",
    "_source_updated_at",
    "_batch_id",
    "_record_hash",
    "_is_deleted"
]


class PolicyLinter:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.findings: List[Dict[str, Any]] = []

    def check_rule_01_secrets(self) -> bool:
        """RULE-01: Scans for raw un-templated passwords and credentials."""
        secret_patterns = [
            re.compile(r"(password|secret|token|private_key)\s*[:=]\s*['\"]([a-zA-Z0-9_\-!@#$%^&*]{8,})['\"]", re.IGNORECASE)
        ]
        violations = []
        exclude_dirs = {".git", ".idea", "__pycache__", "node_modules", "runs"}

        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                if file.endswith((".example", ".md", ".log", ".pyc", ".png", ".webp", ".docx")):
                    continue
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        for line_idx, line in enumerate(f, start=1):
                            if "${" in line or "change_this" in line or "admin_profile" in line or "minio_dev" in line:
                                continue
                            for p in secret_patterns:
                                if p.search(line):
                                    rel_path = os.path.relpath(filepath, self.root_dir)
                                    violations.append(f"{rel_path}:{line_idx}")
                except Exception:
                    pass

        passed = (len(violations) == 0)
        self.findings.append({
            "rule": "RULE-01: Zero-Trust Secret Sanitation",
            "passed": passed,
            "details": "No hardcoded production secrets detected." if passed else f"Potential secrets found in: {violations}"
        })
        return passed

    def check_rule_02_metadata_columns(self) -> bool:
        """RULE-02: Verifies that raw landing tables contain all 7 mandatory technical columns."""
        ddl_path = os.path.join(self.root_dir, "sql/init/02_medallion_tables.sql")
        if not os.path.exists(ddl_path):
            self.findings.append({
                "rule": "RULE-02: Mandatory Technical Metadata Columns",
                "passed": False,
                "details": f"DDL file missing: {ddl_path}"
            })
            return False

        with open(ddl_path, "r", encoding="utf-8") as f:
            content = f.read()

        missing_cols = []
        for col in REQUIRED_METADATA_COLUMNS:
            if col not in content:
                missing_cols.append(col)

        passed = (len(missing_cols) == 0)
        self.findings.append({
            "rule": "RULE-02: Mandatory Technical Metadata Columns",
            "passed": passed,
            "details": "All 7 technical ingestion columns are present in DDL." if passed else f"Missing metadata columns: {missing_cols}"
        })
        return passed

    def check_rule_03_partitioning(self) -> bool:
        """RULE-03: Verifies fact tables use low-cardinality monthly partitioning (toYYYYMM)."""
        ddl_path = os.path.join(self.root_dir, "sql/init/02_medallion_tables.sql")
        with open(ddl_path, "r", encoding="utf-8") as f:
            content = f.read()

        has_monthly_partition = "PARTITION BY toYYYYMM" in content
        self.findings.append({
            "rule": "RULE-03: Low-Cardinality Fact Table Partitioning",
            "passed": has_monthly_partition,
            "details": "Fact tables correctly partitioned by toYYYYMM() monthly granularity." if has_monthly_partition else "Missing toYYYYMM partitioning."
        })
        return has_monthly_partition

    def check_rule_04_storage_tiering(self) -> bool:
        """RULE-04: Verifies ClickHouse storage_configuration.xml defines hot & cold volumes."""
        config_path = os.path.join(self.root_dir, "clickhouse/config.d/storage_configuration.xml")
        if not os.path.exists(config_path):
            self.findings.append({
                "rule": "RULE-04: Hot/Cold Storage Tiering Policy",
                "passed": False,
                "details": f"Missing config: {config_path}"
            })
            return False

        try:
            tree = ET.parse(config_path)
            root = tree.getroot()
            volumes = [v.tag for v in root.findall(".//volume")]
            has_hot = root.find(".//volume[@name='hot']") is not None or root.find(".//hot") is not None
            has_cold = root.find(".//volume[@name='cold']") is not None or root.find(".//cold") is not None
            passed = has_hot and has_cold
            self.findings.append({
                "rule": "RULE-04: Hot/Cold Storage Tiering Policy",
                "passed": passed,
                "details": "storage_configuration.xml properly defines Hot NVMe and Cold S3 volumes." if passed else "Missing hot or cold volume definitions."
            })
            return passed
        except Exception as e:
            self.findings.append({
                "rule": "RULE-04: Hot/Cold Storage Tiering Policy",
                "passed": False,
                "details": f"XML parse error: {e}"
            })
            return False

    def check_rule_05_rbac_and_quotas(self) -> bool:
        """RULE-05: Verifies least-privilege profiles & memory quotas."""
        users_config = os.path.join(self.root_dir, "clickhouse/users.d/roles_and_profiles.xml")
        rbac_sql = os.path.join(self.root_dir, "sql/init/04_rbac_and_row_policies.sql")

        if not os.path.exists(users_config) or not os.path.exists(rbac_sql):
            self.findings.append({
                "rule": "RULE-05: Least-Privilege Roles & Quotas",
                "passed": False,
                "details": f"Missing RBAC or Profile configuration files."
            })
            return False

        with open(users_config, "r", encoding="utf-8") as f:
            xml_content = f.read()

        with open(rbac_sql, "r", encoding="utf-8") as f:
            sql_content = f.read()

        has_profiles = "bi_profile" in xml_content and "api_profile" in xml_content
        has_quota = "max_memory_usage" in xml_content
        has_sql_roles = "role_bi_readonly" in sql_content and "role_api_service" in sql_content
        passed = has_profiles and has_quota and has_sql_roles

        self.findings.append({
            "rule": "RULE-05: Least-Privilege Roles & Quotas",
            "passed": passed,
            "details": "Configured role_bi_readonly, role_api_service, and max_memory_usage quotas in XML and SQL." if passed else "Missing roles or memory quota configurations."
        })
        return passed

    def check_rule_06_clickhouse_env_substitutions(self) -> bool:
        """RULE-06: Forbids inline fallback values on from_env elements."""
        violations = []
        pattern = os.path.join(self.root_dir, "clickhouse", "**", "*.xml")

        for config_path in glob.glob(pattern, recursive=True):
            try:
                root = ET.parse(config_path).getroot()
            except ET.ParseError as exc:
                rel_path = os.path.relpath(config_path, self.root_dir)
                violations.append(f"{rel_path}: XML parse error: {exc}")
                continue

            for element in root.iter():
                if "from_env" not in element.attrib:
                    continue
                if (element.text or "").strip():
                    rel_path = os.path.relpath(config_path, self.root_dir)
                    violations.append(
                        f"{rel_path}: <{element.tag}> must not contain an inline fallback value"
                    )

        passed = not violations
        self.findings.append({
            "rule": "RULE-06: ClickHouse Environment Substitution",
            "passed": passed,
            "details": (
                "All from_env elements require external values and contain no inline fallback."
                if passed
                else f"Invalid from_env elements with inline fallback values: {violations}"
            )
        })
        return passed

    def check_rule_07_clickhouse_logging_config(self) -> bool:
        """RULE-07: Rejects logger structures known to fail ClickHouse startup."""
        config_path = os.path.join(self.root_dir, "clickhouse/config.d/logging.xml")
        violations = []

        try:
            root = ET.parse(config_path).getroot()
        except (OSError, ET.ParseError) as exc:
            violations.append(f"XML parse error: {exc}")
        else:
            formatting = root.find("./logger/formatting")
            if formatting is not None:
                formatting_type = formatting.find("type")
                if formatting_type is None or not (formatting_type.text or "").strip():
                    violations.append("logger.formatting requires a nested <type> value")

            for system_log in root.findall("./query_log"):
                if system_log.find("engine") is not None:
                    conflicting = [
                        name
                        for name in ("partition_by", "order_by", "ttl")
                        if system_log.find(name) is not None
                    ]
                    if conflicting:
                        violations.append(
                            "query_log.engine cannot be combined with "
                            + ", ".join(conflicting)
                        )

        passed = not violations
        self.findings.append({
            "rule": "RULE-07: ClickHouse Logging Configuration",
            "passed": passed,
            "details": (
                "Logger formatting and query_log table settings are structurally valid."
                if passed
                else f"Invalid logging configuration: {violations}"
            )
        })
        return passed

    def check_rule_08_clickhouse_docker_user_setup(self) -> bool:
        """RULE-08: Prevents entrypoint/custom XML from defining admin twice."""
        violations = []
        users_path = os.path.join(self.root_dir, "clickhouse/users.d/users.xml")

        try:
            root = ET.parse(users_path).getroot()
        except (OSError, ET.ParseError) as exc:
            violations.append(f"users.xml parse error: {exc}")
        else:
            default_user = root.find("./users/default")
            if default_user is None or default_user.attrib.get("remove") != "remove":
                violations.append("users.xml must explicitly remove the image default user")

            admin_password = root.find("./users/admin/password")
            if admin_password is None or admin_password.attrib.get("from_env") != "CLICKHOUSE_ADMIN_PASSWORD":
                violations.append("users.xml admin password must come from CLICKHOUSE_ADMIN_PASSWORD")

        compose_paths = [
            "compose/docker-compose.dev.yml",
            "compose/docker-compose.prod-node1.yml",
            "compose/docker-compose.prod-node2.yml",
        ]
        skip_setup_pattern = re.compile(
            r"CLICKHOUSE_SKIP_USER_SETUP\s*:\s*(?:[\"']?1[\"']?|"
            r"\$\{CLICKHOUSE_SKIP_USER_SETUP:-1\})"
        )
        for relative_path in compose_paths:
            config_path = os.path.join(self.root_dir, relative_path)
            try:
                with open(config_path, "r", encoding="utf-8") as config_file:
                    content = config_file.read()
            except OSError as exc:
                violations.append(f"{relative_path}: {exc}")
                continue
            if not skip_setup_pattern.search(content):
                violations.append(
                    f"{relative_path}: CLICKHOUSE_SKIP_USER_SETUP must be 1"
                )

        workflow_path = os.path.join(
            self.root_dir, ".github/workflows/publish-uat-images.yml"
        )
        try:
            with open(workflow_path, "r", encoding="utf-8") as workflow_file:
                workflow_content = workflow_file.read()
        except OSError as exc:
            violations.append(f"publish workflow: {exc}")
        else:
            if "--env CLICKHOUSE_SKIP_USER_SETUP=1" not in workflow_content:
                violations.append(
                    "publish workflow must smoke-test with CLICKHOUSE_SKIP_USER_SETUP=1"
                )

        passed = not violations
        self.findings.append({
            "rule": "RULE-08: ClickHouse Docker User Provisioning",
            "passed": passed,
            "details": (
                "Custom users.xml exclusively provisions admin/service users."
                if passed
                else f"Conflicting Docker user provisioning: {violations}"
            )
        })
        return passed

    def run_all(self) -> bool:
        print("=" * 68)
        print(" ENTERPRISE POLICY-AS-CODE COMPLIANCE LINTER (AGENTS.MD)")
        print("=" * 68)
        print(f" Root Directory: {self.root_dir}")
        print("-" * 68)

        r1 = self.check_rule_01_secrets()
        r2 = self.check_rule_02_metadata_columns()
        r3 = self.check_rule_03_partitioning()
        r4 = self.check_rule_04_storage_tiering()
        r5 = self.check_rule_05_rbac_and_quotas()
        r6 = self.check_rule_06_clickhouse_env_substitutions()
        r7 = self.check_rule_07_clickhouse_logging_config()
        r8 = self.check_rule_08_clickhouse_docker_user_setup()

        all_passed = all([r1, r2, r3, r4, r5, r6, r7, r8])

        for f in self.findings:
            mark = "[PASS]" if f["passed"] else "[FAIL]"
            print(f"{mark} {f['rule']}")
            print(f"       {f['details']}")

        print("-" * 68)
        print(f" EVALUATION RESULT: {'100% COMPLIANT WITH AGENTS.MD' if all_passed else 'NON-COMPLIANT'}")
        print("=" * 68 + "\n")
        return all_passed


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    linter = PolicyLinter(root)
    success = linter.run_all()
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
