"""Check non-secret deployment inputs; never prints secret contents."""
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit


def check():
    errors = []
    image = os.getenv("INSIGHT_PROD_IMAGE", "")
    if not re.fullmatch(r"[^\s@]+@sha256:[0-9a-f]{64}", image):
        errors.append("INSIGHT_PROD_IMAGE must use an immutable sha256 digest")
    try:
        port = int(os.getenv("INSIGHT_PROD_PORT", ""))
        if not 1024 <= port <= 65535:
            raise ValueError
    except ValueError:
        errors.append("INSIGHT_PROD_PORT must be a port from 1024 to 65535")
    issuer = urlsplit(os.getenv("INSIGHT_OIDC_ISSUER", ""))
    if issuer.scheme != "https" or not issuer.hostname:
        errors.append("INSIGHT_OIDC_ISSUER must be an HTTPS issuer")
    for name in ("INSIGHT_OIDC_CLIENT_ID", "INSIGHT_OIDC_GROUP_VIEWER", "INSIGHT_OIDC_GROUP_AUTHOR", "INSIGHT_OIDC_GROUP_ADMIN"):
        if not os.getenv(name, "").strip():
            errors.append(f"{name} is required")
    for name in ("INSIGHT_PROD_SECRET_KEY_SOURCE", "INSIGHT_PROD_METADATA_URI_SOURCE", "INSIGHT_PROD_REDIS_URI_SOURCE", "INSIGHT_PROD_OIDC_SECRET_SOURCE", "INSIGHT_PROD_METADATA_CA_SOURCE", "INSIGHT_PROD_REDIS_CA_SOURCE", "INSIGHT_PROD_IDENTITY_CA_SOURCE"):
        value = os.getenv(name, "")
        path = Path(value)
        if not value or not path.is_absolute() or not path.is_file():
            errors.append(f"{name} must reference an existing absolute file path")
        elif path.stat().st_mode & 0o007:
            errors.append(f"{name} must not be accessible by other users")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Basic production input checks passed. This is not a security or deployment approval.")
    return 0


if __name__ == "__main__":
    sys.exit(check())
