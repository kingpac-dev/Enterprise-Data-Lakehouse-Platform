-- =============================================================================
-- 01_databases.sql: Medallion Layer Database Namespaces
-- =============================================================================

-- 1. Raw / Bronze Layer: Immutable source landing and replayable ingested data
CREATE DATABASE IF NOT EXISTS raw
COMMENT 'Bronze Layer: Source-aligned immutable raw data with technical metadata';

-- 2. Core / Silver Layer: Cleaned, normalized, deduplicated, and conformed entities
CREATE DATABASE IF NOT EXISTS core
COMMENT 'Silver Layer: Cleaned, deduplicated, and conformed enterprise entities';

-- 3. Mart / Gold Layer: Dimensional facts, dimensions, and business domain aggregates
CREATE DATABASE IF NOT EXISTS mart
COMMENT 'Gold Layer: Dimensional star-schemas, business marts, and KPI aggregates';

-- 4. Serving Layer: Dashboard and API optimized views, materialized views, and caches
CREATE DATABASE IF NOT EXISTS serving
COMMENT 'Serving Layer: Sub-second pre-aggregated views and BI endpoints';
