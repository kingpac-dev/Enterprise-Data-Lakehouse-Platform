"""
Base Ingestion Connector
========================
Provides abstract lifecycle, state watermarking, technical metadata tagging,
and ClickHouse ingestion for all data source connectors.
"""

import abc
import os
import json
import uuid
import hashlib
import datetime
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional


class BaseConnector(abc.ABC):
    def __init__(
        self,
        source_system: str,
        source_table: str,
        target_database: str = "raw",
        target_table: str = "orders_landing",
        state_dir: str = ".state",
    ):
        self.source_system = source_system
        self.source_table = source_table
        self.target_database = target_database
        self.target_table = target_table
        self.state_dir = state_dir
        os.makedirs(self.state_dir, exist_ok=True)
        self.state_file = os.path.join(self.state_dir, f"{self.source_system}_{self.source_table}.json")

        self.clickhouse_host = os.getenv("CLICKHOUSE_HOST", "localhost")
        self.clickhouse_port = int(os.getenv("CLICKHOUSE_PORT_HTTP", "18123"))
        self.clickhouse_user = os.getenv("CLICKHOUSE_ETL_USER", os.getenv("CLICKHOUSE_ADMIN_USER", "admin"))
        self.clickhouse_password = os.getenv("CLICKHOUSE_ETL_PASSWORD", os.getenv("CLICKHOUSE_ADMIN_PASSWORD", "change_this_admin_password_in_prod"))

    def get_watermark(self) -> Optional[str]:
        """Loads last high-watermark timestamp or incremental ID."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("last_watermark")
            except Exception as e:
                print(f"[WARN] Failed to read state file {self.state_file}: {e}")
        return None

    def save_watermark(self, watermark: str):
        """Persists high-watermark to local state file."""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump({
                    "source_system": self.source_system,
                    "source_table": self.source_table,
                    "last_watermark": watermark,
                    "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }, f, indent=2)
        except Exception as e:
            print(f"[WARN] Failed to save watermark to {self.state_file}: {e}")

    @abc.abstractmethod
    def extract(self, watermark: Optional[str]) -> List[Dict[str, Any]]:
        """Extracts records from source using watermark."""
        pass

    def enrich_metadata(self, raw_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enriches raw records with the mandatory 7 technical metadata columns."""
        batch_id = str(uuid.uuid4())
        now = datetime.datetime.now(datetime.timezone.utc)
        now_str = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        enriched = []
        for r in raw_records:
            payload_str = json.dumps(r, sort_keys=True)
            record_hash = hashlib.md5(payload_str.encode("utf-8")).hexdigest()
            source_updated_at = r.get("updated_at") or r.get("order_timestamp") or now_str

            rec = dict(r)
            rec["raw_payload"] = payload_str
            rec["_source_system"] = self.source_system
            rec["_source_table"] = self.source_table
            rec["_ingested_at"] = now_str
            rec["_source_updated_at"] = str(source_updated_at)
            rec["_batch_id"] = batch_id
            rec["_record_hash"] = record_hash
            rec["_is_deleted"] = int(r.get("is_deleted", 0))

            enriched.append(rec)
        return enriched

    def load_to_clickhouse(self, records: List[Dict[str, Any]]) -> int:
        """Streams enriched records into ClickHouse raw landing table."""
        if not records:
            print(f"[{self.source_system}] No records to load.")
            return 0

        url = f"http://{self.clickhouse_host}:{self.clickhouse_port}/"
        query = f"INSERT INTO {self.target_database}.{self.target_table} FORMAT JSONEachRow"
        headers = {
            "X-ClickHouse-User": self.clickhouse_user,
            "X-ClickHouse-Key": self.clickhouse_password,
            "X-ClickHouse-Setting": "async_insert=1,wait_for_async_insert=1",
        }
        data = "\n".join(json.dumps(r) for r in records).encode("utf-8")

        req = urllib.request.Request(f"{url}?query={urllib.parse.quote(query)}", data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp.read()
            print(f"[{self.source_system}] Successfully ingested {len(records)} records into {self.target_database}.{self.target_table}.")
            return len(records)
        except urllib.error.URLError as e:
            print(f"[{self.source_system}] Ingestion failed: {e}")
            raise

    def run(self) -> int:
        """Executes full extraction, enrichment, and loading pipeline."""
        print(f"[{self.source_system}] Starting connector for {self.source_table}...")
        watermark = self.get_watermark()
        print(f"[{self.source_system}] Current watermark: {watermark}")

        raw_records = self.extract(watermark)
        if not raw_records:
            print(f"[{self.source_system}] No new data found.")
            return 0

        enriched_records = self.enrich_metadata(raw_records)
        loaded_count = self.load_to_clickhouse(enriched_records)

        # Update high-watermark to latest timestamp or max ID
        latest_ts = max(r.get("order_timestamp", r.get("updated_at", "")) for r in raw_records)
        if latest_ts:
            self.save_watermark(str(latest_ts))
            print(f"[{self.source_system}] High-watermark advanced to: {latest_ts}")

        return loaded_count
