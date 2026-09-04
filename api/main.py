"""
Enterprise Data Lakehouse Platform - Serving REST API
=====================================================
FastAPI microservice providing governed, sub-second API access to ClickHouse
serving views and real-time operational data quality metrics.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import sales, metrics

app = FastAPI(
    title="Enterprise Data Lakehouse Serving API",
    description="High-performance, sub-second analytical serving microservice on ClickHouse 26.8 LTS",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for Web/BI Dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
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
