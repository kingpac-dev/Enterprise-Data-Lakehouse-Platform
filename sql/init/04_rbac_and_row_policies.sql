-- =============================================================================
-- 04_rbac_and_row_policies.sql: Enterprise Least-Privilege RBAC & Security
-- =============================================================================

-- 1. Create Roles
CREATE ROLE IF NOT EXISTS role_platform_admin;
CREATE ROLE IF NOT EXISTS role_data_engineer;
CREATE ROLE IF NOT EXISTS role_etl_service;
CREATE ROLE IF NOT EXISTS role_bi_readonly;
CREATE ROLE IF NOT EXISTS role_api_service;
CREATE ROLE IF NOT EXISTS role_monitoring_service;

-- 2. Platform Admin Grants
GRANT ALL ON *.* TO role_platform_admin WITH GRANT OPTION;

-- 3. Data Engineer Grants (DDL, Select, Insert, Alter across data layers)
GRANT ALL ON raw.* TO role_data_engineer;
GRANT ALL ON core.* TO role_data_engineer;
GRANT ALL ON mart.* TO role_data_engineer;
GRANT ALL ON serving.* TO role_data_engineer;

-- 4. ETL Service Grants (Write-only to raw landing; read access to core for lookup)
GRANT INSERT, SELECT ON raw.* TO role_etl_service;
GRANT SELECT ON core.* TO role_etl_service;

-- 5. BI Readonly Grants (Read-only access strictly restricted to mart and serving layers)
GRANT SELECT ON mart.* TO role_bi_readonly;
GRANT SELECT ON serving.* TO role_bi_readonly;

-- 6. API Service Grants (Read-only on serving layer views only)
GRANT SELECT ON serving.* TO role_api_service;

-- 7. Monitoring Service Grants (System tables only)
GRANT SELECT ON system.* TO role_monitoring_service;

-- 8. XML-backed users are provisioned from users.xml. ClickHouse 26.8 treats
-- users_xml storage as read-only, so user grants must be declared in XML rather
-- than assigned here via SQL.

-- 9. Row-Level Security Policy Template (Example: Branch-level segregation)
-- Restricts BI users with specific branch settings to view only authorized records
-- CREATE ROW POLICY IF NOT EXISTS branch_isolation_policy ON mart.fact_sales
--     FOR SELECT
--     USING (branch_id = currentUser())
--     TO role_bi_readonly;
