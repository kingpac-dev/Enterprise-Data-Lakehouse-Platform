"""Production candidate configuration; fail closed on missing or unsafe inputs."""

import logging
import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from flask_appbuilder.security.manager import AUTH_OAUTH
from prod_security import KingPacSecurityManager
from redis import Redis


def required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required setting: {name}")
    return value


def secret(name):
    try:
        value = Path(required(name)).read_text(encoding="utf-8").strip()
    except OSError:
        raise RuntimeError(f"Cannot read secret file: {name}") from None
    if not value:
        raise RuntimeError(f"Empty secret file: {name}")
    return value


def validated_uri(value, scheme, required_query, allowed_query):
    try:
        parts = urlsplit(value)
        _ = parts.port
        query = parse_qs(parts.query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        raise RuntimeError("Invalid connection URI") from None
    if (parts.scheme != scheme or not parts.hostname or not parts.username or not parts.password
            or not parts.path.strip("/") or parts.fragment or set(query) - allowed_query
            or any(query.get(key) != [expected] for key, expected in required_query.items())):
        raise RuntimeError("Connection URI does not meet production TLS/authentication requirements")
    return value


SECRET_KEY = secret("INSIGHT_SECRET_KEY_FILE")
if len(SECRET_KEY) < 32:
    raise RuntimeError("Superset secret key must contain at least 32 characters")
SQLALCHEMY_DATABASE_URI = validated_uri(
    secret("INSIGHT_METADATA_URI_FILE"), "postgresql+psycopg2",
    {"sslmode": "verify-full", "sslrootcert": "/run/secrets/metadata_ca"},
    {"sslmode", "sslrootcert", "connect_timeout", "application_name"},
)
_redis_url = validated_uri(
    secret("INSIGHT_REDIS_URI_FILE"), "rediss",
    {"ssl_cert_reqs": "required", "ssl_check_hostname": "true", "ssl_ca_certs": "/run/secrets/redis_ca"},
    {"ssl_cert_reqs", "ssl_check_hostname", "ssl_ca_certs", "socket_timeout", "socket_connect_timeout"},
)
SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 5}


def redis_cache(prefix, timeout):
    return {"CACHE_TYPE": "RedisCache", "CACHE_REDIS_URL": _redis_url,
            "CACHE_KEY_PREFIX": prefix, "CACHE_DEFAULT_TIMEOUT": timeout}


CACHE_CONFIG = redis_cache("kingpac_prod_meta_", 300)
DATA_CACHE_CONFIG = redis_cache("kingpac_prod_data_", 300)
FILTER_STATE_CACHE_CONFIG = redis_cache("kingpac_prod_filter_", 86400)
EXPLORE_FORM_DATA_CACHE_CONFIG = redis_cache("kingpac_prod_explore_", 86400)
RATELIMIT_STORAGE_URI = _redis_url
SESSION_SERVER_SIDE = True
SESSION_TYPE = "redis"
SESSION_REDIS = Redis.from_url(_redis_url)
SESSION_KEY_PREFIX = "kingpac_prod_session_"
SESSION_USE_SIGNER = True
SESSION_PERMANENT = True
PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
ENABLE_PROXY_FIX = True
PROXY_FIX_CONFIG = {"x_for": 1, "x_proto": 1, "x_host": 1, "x_port": 1, "x_prefix": 1}
PREFERRED_URL_SCHEME = "https"
WTF_CSRF_ENABLED = True
FEATURE_FLAGS = {"DASHBOARD_RBAC": True, "CACHE_QUERY_BY_USER": True, "ENABLE_TEMPLATE_PROCESSING": False}
ROW_LIMIT = 5000
SQL_MAX_ROW = 5000
APP_NAME = "KingPac Enterprise Insight Platform"
# FAB can log OAuth responses at DEBUG; keep authentication logs at INFO.
LOG_LEVEL = logging.INFO
logging.getLogger("flask_appbuilder.security.views").setLevel(logging.INFO)

KINGPAC_OIDC_ISSUER = required("INSIGHT_OIDC_ISSUER").rstrip("/")
_issuer = urlsplit(KINGPAC_OIDC_ISSUER)
if _issuer.scheme != "https" or not _issuer.hostname or _issuer.username is not None or _issuer.password is not None or _issuer.query or _issuer.fragment:
    raise RuntimeError("Keycloak issuer must be an HTTPS URL without credentials, query or fragment")
KINGPAC_USERINFO_URL = f"{KINGPAC_OIDC_ISSUER}/protocol/openid-connect/userinfo"
_groups = [required("INSIGHT_OIDC_GROUP_VIEWER"), required("INSIGHT_OIDC_GROUP_AUTHOR"),
           required("INSIGHT_OIDC_GROUP_ADMIN")]
if len(set(_groups)) != 3:
    raise RuntimeError("Viewer, author, and admin Keycloak groups must be distinct")
AUTH_TYPE = AUTH_OAUTH
AUTH_USER_REGISTRATION = True
AUTH_USER_REGISTRATION_ROLE = None
AUTH_ROLES_SYNC_AT_LOGIN = True
AUTH_ROLES_MAPPING = {_groups[0]: ["Gamma"], _groups[1]: ["Alpha"], _groups[2]: ["Admin"]}
CUSTOM_SECURITY_MANAGER = KingPacSecurityManager
OAUTH_PROVIDERS = [{
    "name": "keycloak", "token_key": "access_token", "icon": "fa-circle-o",
    "remote_app": {
        "server_metadata_url": f"{KINGPAC_OIDC_ISSUER}/.well-known/openid-configuration",
        "api_base_url": f"{KINGPAC_OIDC_ISSUER}/protocol/openid-connect/",
        "client_id": required("INSIGHT_OIDC_CLIENT_ID"),
        "client_secret": secret("INSIGHT_OIDC_CLIENT_SECRET_FILE"),
        "client_kwargs": {"scope": "openid email profile", "code_challenge_method": "S256", "default_timeout": 10},
    },
}]

# Explicit CSP: no third-party scripts, frames or connections by default.
TALISMAN_ENABLED = True
TALISMAN_CONFIG = {
    "content_security_policy": {
        "base-uri": ["'self'"], "default-src": ["'self'"], "img-src": ["'self'", "blob:", "data:"],
        "worker-src": ["'self'", "blob:"], "connect-src": ["'self'"], "object-src": "'none'",
        "style-src": ["'self'", "'unsafe-inline'"], "font-src": ["'self'"],
        "script-src": ["'self'", "'strict-dynamic'"],
    },
    "content_security_policy_nonce_in": ["script-src"], "force_https": False,
    "session_cookie_secure": True,
}
