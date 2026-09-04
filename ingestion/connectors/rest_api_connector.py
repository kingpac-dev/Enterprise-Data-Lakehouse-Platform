"""
REST API Ingestion Connector
============================
Extracts data from external REST endpoints with pagination, token authentication,
and automatic rate limiting.
"""

import os
import json
import time
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from .base_connector import BaseConnector


class RestApiConnector(BaseConnector):
    def __init__(
        self,
        api_endpoint: str = "https://api.example.com/v1/orders",
        api_token_env: str = "SOURCE_API_TOKEN",
        source_system: str = "REST_API_CRM",
        source_table: str = "orders",
        page_size: int = 100,
        max_pages: int = 10,
        **kwargs
    ):
        super().__init__(source_system=source_system, source_table=source_table, **kwargs)
        self.api_endpoint = api_endpoint
        self.api_token = os.getenv(api_token_env, "")
        self.page_size = page_size
        self.max_pages = max_pages

    def extract(self, watermark: Optional[str]) -> List[Dict[str, Any]]:
        """Extracts pages from REST API endpoint."""
        records = []
        headers = {
            "Accept": "application/json",
            "User-Agent": "Enterprise-Lakehouse-Extractor/1.0",
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        page = 1
        while page <= self.max_pages:
            url = f"{self.api_endpoint}?page={page}&limit={self.page_size}"
            if watermark:
                url += f"&since={urllib.parse.quote(watermark)}"

            print(f"[{self.source_system}] Requesting page {page}...")
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    batch = data.get("data", data if isinstance(data, list) else [])
                    if not batch:
                        break
                    records.extend(batch)
                    if len(batch) < self.page_size:
                        break
            except urllib.error.HTTPError as e:
                if e.code == 404 or "example.com" in self.api_endpoint:
                    print(f"[{self.source_system}] Simulated mock endpoint or 404. Terminating pagination.")
                    break
                else:
                    print(f"[{self.source_system}] HTTP Error {e.code}: {e}")
                    break
            except Exception as e:
                print(f"[{self.source_system}] API extraction error: {e}")
                break

            page += 1
            time.sleep(0.1)  # Gentle rate limiting

        return records
