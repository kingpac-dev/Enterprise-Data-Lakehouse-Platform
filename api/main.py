"""
Enterprise Data Lakehouse Platform - Serving REST API
=====================================================
FastAPI microservice providing governed, sub-second API access to ClickHouse
serving views and real-time operational data quality metrics.
"""

import os
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import metrics, sales

app = FastAPI(
    title="Enterprise Data Lakehouse Serving API",
    description="High-performance, sub-second analytical serving microservice on ClickHouse 26.8 LTS",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

def cors_settings() -> tuple[list[str], bool]:
    """Allow only explicit browser origins; CORS is not API authentication."""
    origins = []
    for item in os.getenv("API_CORS_ALLOWED_ORIGINS", "").split(","):
        origin = item.strip()
        if not origin:
            continue
        try:
            parts = urlsplit(origin)
            # Reading port validates its syntax and range.
            _ = parts.port
        except ValueError as exc:
            raise ValueError("Invalid API CORS origin") from exc
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or parts.path
            or parts.query
            or parts.fragment
            or "*" in origin
            or any(char.isspace() for char in origin)
        ):
            raise ValueError("API CORS origins must be explicit HTTP(S) origins")
        if origin not in origins:
            origins.append(origin)
    credentials_setting = os.getenv("API_CORS_ALLOW_CREDENTIALS", "false").lower()
    if credentials_setting not in {"true", "false"}:
        raise ValueError("API_CORS_ALLOW_CREDENTIALS must be true or false")
    return origins, credentials_setting == "true"


# An empty allowlist disables cross-origin browser access by default.
_allowed_origins, _allow_credentials = cors_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["GET"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(sales.router)
app.include_router(metrics.router)


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": "lakehouse-serving-api",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
