"""Fail-closed, non-secret-printing preflight for the one-node production stack."""

from __future__ import annotations

import ipaddress
import os
import re
import sys
from urllib.parse import urlparse


REQUIRED = (
    "CLICKHOUSE_SINGLE_IMAGE",
    "PROD_BIND_IP",
    "CLICKHOUSE_ADMIN_PASSWORD",
    "CLICKHOUSE_ETL_PASSWORD",
    "CLICKHOUSE_BI_PASSWORD",
    "CLICKHOUSE_API_PASSWORD",
    "CLICKHOUSE_MONITORING_PASSWORD",
    "CLICKHOUSE_S3_ENDPOINT",
    "CLICKHOUSE_S3_ACCESS_KEY",
    "CLICKHOUSE_S3_SECRET_KEY",
    "S3_REGION",
)
SECRET_NAMES = tuple(name for name in REQUIRED if "PASSWORD" in name or "KEY" in name)
RFC1918 = tuple(
    ipaddress.ip_network(cidr) for cidr in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)


def validate(values: dict[str, str]) -> list[str]:
    errors = [f"{name}: required" for name in REQUIRED if not values.get(name, "").strip()]
    if errors:
        return errors

    image = values["CLICKHOUSE_SINGLE_IMAGE"]
    if not re.fullmatch(r"[^\s@]+@sha256:[0-9a-fA-F]{64}", image):
        errors.append("CLICKHOUSE_SINGLE_IMAGE: use an approved image@sha256:<64 hex> reference")

    try:
        bind_ip = ipaddress.ip_address(values["PROD_BIND_IP"])
        if not isinstance(bind_ip, ipaddress.IPv4Address) or not any(bind_ip in net for net in RFC1918):
            errors.append("PROD_BIND_IP: use an approved RFC1918 IPv4 address on this host")
    except ValueError:
        errors.append("PROD_BIND_IP: invalid IPv4 address")

    s3 = urlparse(values["CLICKHOUSE_S3_ENDPOINT"])
    if s3.scheme != "https" or not s3.hostname or s3.hostname in {"localhost", "127.0.0.1"}:
        errors.append("CLICKHOUSE_S3_ENDPOINT: use an approved independent HTTPS object-store URL")
    if s3.hostname == values["PROD_BIND_IP"]:
        errors.append("CLICKHOUSE_S3_ENDPOINT: object store cannot be the ClickHouse host")
    if s3.username or s3.password or s3.query or s3.fragment:
        errors.append("CLICKHOUSE_S3_ENDPOINT: URL must not contain credentials, query or fragment")
    if not s3.path.endswith("/"):
        errors.append("CLICKHOUSE_S3_ENDPOINT: path must end with /")

    for name in SECRET_NAMES:
        value = values[name].strip()
        if any(marker in value.lower() for marker in ("change_this", "validation_only", "<secret", "tbd")):
            errors.append(f"{name}: placeholder value is not permitted")

    return errors


def main() -> int:
    errors = validate(dict(os.environ))
    for error in errors:
        print(f"FAIL {error}", file=sys.stderr)
    if errors:
        return 1
    print("PASS one-node production environment format; runtime and approval still required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
