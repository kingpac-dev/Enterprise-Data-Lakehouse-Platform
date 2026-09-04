# ==============================================================================
# dbt-clickhouse Runner Container
# ==============================================================================
FROM python:3.11-slim

WORKDIR /usr/app/dbt

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dbt-clickhouse adapter
RUN pip install --no-cache-dir \
    dbt-core==1.8.6 \
    dbt-clickhouse==1.8.4

# Copy dbt project files
COPY . /usr/app/dbt/

# Default entrypoint runs dbt
ENTRYPOINT ["dbt"]
CMD ["run", "--profiles-dir", "."]
