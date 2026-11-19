"""Single-host UAT configuration; production requires a separately reviewed design."""

import os
from urllib.parse import quote


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


SECRET_KEY = required("SUPERSET_SECRET_KEY")
if len(SECRET_KEY) < 32:
    raise RuntimeError("SUPERSET_SECRET_KEY must be at least 32 characters")
_user = quote(required("INSIGHT_POSTGRES_USER"), safe="")
_password = quote(required("INSIGHT_POSTGRES_PASSWORD"), safe="")
_database = quote(required("INSIGHT_POSTGRES_DB"), safe="")
SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{_user}:{_password}@metadata:5432/{_database}"
SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
APP_NAME = "KingPac Enterprise Insight Platform"

_redis_url = "redis://cache:6379/0"


def redis_cache(prefix: str, timeout: int) -> dict:
    return {
        "CACHE_TYPE": "RedisCache",
        "CACHE_REDIS_URL": _redis_url,
        "CACHE_KEY_PREFIX": prefix,
        "CACHE_DEFAULT_TIMEOUT": timeout,
    }


CACHE_CONFIG = redis_cache("insight_meta_", 300)
DATA_CACHE_CONFIG = redis_cache("insight_data_", 300)
FILTER_STATE_CACHE_CONFIG = redis_cache("insight_filter_", 86400)
EXPLORE_FORM_DATA_CACHE_CONFIG = redis_cache("insight_explore_", 86400)
WTF_CSRF_ENABLED = True
AUTH_USER_REGISTRATION = False
ROW_LIMIT = 5000
SQL_MAX_ROW = 5000
FEATURE_FLAGS = {"ENABLE_TEMPLATE_PROCESSING": False}

_https = os.environ.get("INSIGHT_HTTPS_ENABLED", "false").lower() == "true"
# Enable only behind one trusted reverse proxy which overwrites forwarded headers.
ENABLE_PROXY_FIX = _https
PROXY_FIX_CONFIG = {"x_for": 1, "x_proto": 1, "x_host": 1, "x_port": 1, "x_prefix": 1}
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = _https
TALISMAN_ENABLED = True
TALISMAN_CONFIG = {
    "content_security_policy": {
        "base-uri": ["'self'"],
        "default-src": ["'self'"],
        "img-src": ["'self'", "blob:", "data:"],
        "worker-src": ["'self'", "blob:"],
        "connect-src": ["'self'"],
        "object-src": "'none'",
        "style-src": ["'self'", "'unsafe-inline'"],
        "font-src": ["'self'"],
        "script-src": ["'self'", "'strict-dynamic'"],
    },
    "content_security_policy_nonce_in": ["script-src"],
    "force_https": False,  # TLS termination and HTTP-to-HTTPS redirect belong to the proxy.
    "session_cookie_secure": _https,
}
