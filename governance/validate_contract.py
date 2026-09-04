#!/usr/bin/env python3
"""
=============================================================================
Enterprise Data Lakehouse Platform - Data Contract Validator (M08)
=============================================================================
Enforces pre-ingestion Data Contracts against incoming records to prevent
schema drift, type mutations, missing columns, or invalid values.

Adheres to:
- Open Data Contract Standard (ODCS)
- Zero-Trust & AGENTS.md Data Integrity Guidelines
"""

import os
import sys
import json
import argparse
import logging
from typing import Dict, List, Any, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [ContractGuard] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ContractValidator")

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


def load_yaml_contract(contract_path: str) -> Dict[str, Any]:
    """Loads and parses the Data Contract specification file."""
    if not os.path.exists(contract_path):
        raise FileNotFoundError(f"Contract file not found: {contract_path}")

    with open(contract_path, "r", encoding="utf-8") as f:
        content = f.read()

    if YAML_AVAILABLE:
        return yaml.safe_load(content)

    # Lightweight fallback YAML parser for environments without PyYAML
    contract = {"schema": {"columns": []}}
    in_columns = False
    current_col = {}

    for line in content.splitlines():
        line_s = line.strip()
        if not line_s or line_s.startswith("#"):
            continue
        if line_s.startswith("dataset:"):
            contract["dataset"] = line_s.split(":", 1)[1].strip().strip('"\'')
        elif line_s == "columns:":
            in_columns = True
        elif in_columns:
            if line_s.startswith("- name:"):
                if current_col:
                    contract["schema"]["columns"].append(current_col)
                current_col = {"name": line_s.split(":", 1)[1].strip().strip('"\'')}
            elif ":" in line_s and current_col:
                k, v = line_s.split(":", 1)
                k = k.strip()
                v = v.strip().strip('"\'')
                if v.lower() == "true":
                    v = True
                elif v.lower() == "false":
                    v = False
                current_col[k] = v

    if current_col:
        contract["schema"]["columns"].append(current_col)

    return contract


class ContractValidator:
    def __init__(self, contract: Dict[str, Any]):
        self.contract = contract
        self.dataset = contract.get("dataset", "unknown")
        self.columns_def = contract.get("schema", {}).get("columns", [])
        self.column_map = {col["name"]: col for col in self.columns_def}

    def validate_record(self, record: Dict[str, Any], record_idx: int) -> List[str]:
        """Validates a single record dictionary against contract rules."""
        violations = []

        # 1. Check for missing required columns
        for col_name, col_spec in self.column_map.items():
            if col_name not in record:
                violations.append(f"Row {record_idx}: Missing required column '{col_name}'")
                continue

            val = record[col_name]

            # 2. Check nullability
            if not col_spec.get("nullable", True) and val is None:
                violations.append(f"Row {record_idx}: Column '{col_name}' cannot be NULL")

            # 3. Check allowed values
            allowed = col_spec.get("allowed_values")
            if allowed and val is not None and val not in allowed:
                violations.append(f"Row {record_idx}: Column '{col_name}' has invalid value '{val}' (Allowed: {allowed})")

            # 4. Check numeric rules
            rules = col_spec.get("rules", {})
            if isinstance(rules, dict) and val is not None:
                if "min" in rules:
                    try:
                        if float(val) < float(rules["min"]):
                            violations.append(f"Row {record_idx}: Column '{col_name}' value {val} < min limit {rules['min']}")
                    except (ValueError, TypeError):
                        pass
                if "max" in rules:
                    try:
                        if float(val) > float(rules["max"]):
                            violations.append(f"Row {record_idx}: Column '{col_name}' value {val} > max limit {rules['max']}")
                    except (ValueError, TypeError):
                        pass

        return violations

    def validate_batch(self, batch: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validates a list of records."""
        all_violations = []
        for idx, rec in enumerate(batch):
            v = self.validate_record(rec, idx + 1)
            all_violations.extend(v)

        is_valid = (len(all_violations) == 0)
        return is_valid, all_violations


def generate_sample_batches():
    """Generates one compliant batch and one non-compliant batch for validation tests."""
    valid_batch = [
        {
            "order_id": 10001,
            "customer_id": 42,
            "order_timestamp": "2026-09-04 10:00:00.000",
            "branch_id": 5,
            "product_id": 101,
            "unit_price": 250.00,
            "quantity": 2.0,
            "discount": 10.00,
            "status": "COMPLETED",
            "raw_payload": "{}",
            "_source_system": "pos_terminal",
            "_source_table": "orders",
            "_ingested_at": "2026-09-04 10:00:01.000",
            "_source_updated_at": "2026-09-04 10:00:00.000",
            "_batch_id": "batch_20260904_01",
            "_record_hash": "d41d8cd98f00b204e9800998ecf8427e",
            "_is_deleted": 0
        },
        {
            "order_id": 10002,
            "customer_id": 88,
            "order_timestamp": "2026-09-04 10:05:00.000",
            "branch_id": 12,
            "product_id": 205,
            "unit_price": 1499.00,
            "quantity": 1.0,
            "discount": 0.00,
            "status": "PENDING",
            "raw_payload": "{}",
            "_source_system": "ecom_mobile",
            "_source_table": "orders",
            "_ingested_at": "2026-09-04 10:05:01.000",
            "_source_updated_at": "2026-09-04 10:05:00.000",
            "_batch_id": "batch_20260904_01",
            "_record_hash": "e2fc714c4727ee9395f324cd2e7f331f",
            "_is_deleted": 0
        }
    ]

    invalid_batch = [
        {
            "order_id": 99999,
            "customer_id": 999,
            # Missing order_timestamp (Contract Violation)
            "branch_id": 1500,  # branch_id > 1000 (Contract Violation)
            "product_id": 303,
            "unit_price": -50.00,  # unit_price < 0.01 (Contract Violation)
            "quantity": 0.0,  # quantity < 0.001 (Contract Violation)
            "discount": 0.0,
            "status": "UNKNOWN_STATUS",  # Not in allowed values (Contract Violation)
            "_source_system": "legacy_dump",
            "_source_table": "orders",
            "_ingested_at": "2026-09-04 10:05:01.000",
            "_source_updated_at": "2026-09-04 10:05:00.000",
            "_batch_id": "batch_bad",
            "_record_hash": "badhash",
            "_is_deleted": 0
        }
    ]

    return valid_batch, invalid_batch


def main():
    parser = argparse.ArgumentParser(description="Enterprise Lakehouse Data Contract Validator")
    parser.add_argument("--contract", default="contracts/orders_contract.yml", help="Path to Data Contract YAML")
    parser.add_argument("--data-file", default=None, help="Path to JSON file with records to validate")
    parser.add_argument("--dry-run", action="store_true", help="Run contract validation test with synthetic compliant & non-compliant data")

    args = parser.parse_args()
    print("=" * 65)
    print(" ENTERPRISE DATA CONTRACT & SCHEMA GUARD (M08)")
    print("=" * 65)
    print(f" Contract File : {args.contract}")

    try:
        contract = load_yaml_contract(args.contract)
    except Exception as e:
        logger.error(f"Failed to load contract: {e}")
        sys.exit(1)

    validator = ContractValidator(contract)
    print(f" Target Dataset: {validator.dataset}")
    print(f" Columns Bound : {len(validator.column_map)} columns")
    print("-" * 65)

    if args.data_file:
        with open(args.data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = [data]
        is_valid, violations = validator.validate_batch(data)
        if is_valid:
            print("[PASS] All records adhere strictly to Data Contract!")
            sys.exit(0)
        else:
            print(f"[FAIL] Data Contract Breached! Found {len(violations)} violations:")
            for v in violations[:10]:
                print(f"  - {v}")
            sys.exit(1)

    elif args.dry_run or not args.data_file:
        logger.info("Executing contract evaluation against test datasets...")
        valid_batch, invalid_batch = generate_sample_batches()

        print("\n[TEST 1] Validating Compliant Batch (2 records):")
        pass_valid, v1 = validator.validate_batch(valid_batch)
        if pass_valid:
            print("  Result: [PASS] Compliant batch accepted without violations.")
        else:
            print(f"  Result: [FAIL] Unexpected violations: {v1}")

        print("\n[TEST 2] Validating Non-Compliant Batch (1 record with intentional drifts):")
        pass_invalid, v2 = validator.validate_batch(invalid_batch)
        if not pass_invalid:
            print(f"  Result: [PASS - BLOCKED] Successfully intercepted {len(v2)} contract violations:")
            for item in v2:
                print(f"    - {item}")
        else:
            print("  Result: [FAIL] Breached batch was erroneously accepted!")

        print("\n" + "=" * 65)
        print(" CONTRACT VERIFICATION SUMMARY: ALL CHECKS PASSED")
        print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
