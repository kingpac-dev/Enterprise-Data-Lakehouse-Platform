"""
File Drop Connector
===================
Loads batches from dropped CSV or JSON files in a landing folder,
enriches technical metadata, loads into ClickHouse, and moves processed files.
"""

import os
import csv
import json
import shutil
from typing import List, Dict, Any, Optional
from .base_connector import BaseConnector


class FileDropConnector(BaseConnector):
    def __init__(
        self,
        drop_dir: str = "landing_drops",
        archive_dir: str = "landing_archive",
        source_system: str = "FILE_DROP",
        source_table: str = "sales_orders",
        **kwargs
    ):
        super().__init__(source_system=source_system, source_table=source_table, **kwargs)
        self.drop_dir = drop_dir
        self.archive_dir = archive_dir
        os.makedirs(self.drop_dir, exist_ok=True)
        os.makedirs(self.archive_dir, exist_ok=True)

    def extract(self, watermark: Optional[str]) -> List[Dict[str, Any]]:
        """Scans drop directory for pending CSV/JSON files."""
        records = []
        files = sorted(os.listdir(self.drop_dir))

        for fname in files:
            fpath = os.path.join(self.drop_dir, fname)
            if not os.path.isfile(fpath):
                continue

            print(f"[{self.source_system}] Processing file: {fname}")
            try:
                if fname.endswith(".csv"):
                    with open(fpath, "r", encoding="utf-8") as fp:
                        reader = csv.DictReader(fp)
                        for row in reader:
                            # Convert types
                            rec = {
                                "order_id": int(row["order_id"]),
                                "customer_id": int(row["customer_id"]),
                                "order_timestamp": row["order_timestamp"],
                                "branch_id": int(row["branch_id"]),
                                "product_id": int(row["product_id"]),
                                "unit_price": float(row["unit_price"]),
                                "quantity": float(row["quantity"]),
                                "discount": float(row.get("discount", 0.0)),
                                "status": row.get("status", "COMPLETED"),
                                "is_deleted": int(row.get("is_deleted", 0)),
                            }
                            records.append(rec)
                elif fname.endswith(".json"):
                    with open(fpath, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if isinstance(data, list):
                            records.extend(data)
                        elif isinstance(data, dict):
                            records.append(data)

                # Move to archive directory
                shutil.move(fpath, os.path.join(self.archive_dir, fname))
            except Exception as e:
                print(f"[ERROR] Failed to process {fname}: {e}")

        return records
