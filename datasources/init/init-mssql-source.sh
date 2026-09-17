#!/usr/bin/env bash
set -euo pipefail

database="${MSSQL_DATABASE:-source_uat}"
app_user="${MSSQL_APP_USER:-source_app}"

if [[ ! "${database}" =~ ^[A-Za-z][A-Za-z0-9_]*$ ]]; then
  echo "Invalid MSSQL_DATABASE; use letters, digits, and underscores only." >&2
  exit 1
fi

if [[ ! "${app_user}" =~ ^[A-Za-z][A-Za-z0-9_]*$ ]]; then
  echo "Invalid MSSQL_APP_USER; use letters, digits, and underscores only." >&2
  exit 1
fi

escaped_password="${MSSQL_APP_PASSWORD//\'/\'\'}"
sqlcmd=/opt/mssql-tools18/bin/sqlcmd

"${sqlcmd}" -S "${MSSQL_HOST:-source-mssql}" -U sa -P "${MSSQL_SA_PASSWORD}" -C -b -Q "
IF DB_ID(N'${database}') IS NULL CREATE DATABASE [${database}];
IF SUSER_ID(N'${app_user}') IS NULL CREATE LOGIN [${app_user}] WITH PASSWORD = N'${escaped_password}';
"

"${sqlcmd}" -S "${MSSQL_HOST:-source-mssql}" -U sa -P "${MSSQL_SA_PASSWORD}" -C -b -d "${database}" -Q "
IF USER_ID(N'${app_user}') IS NULL CREATE USER [${app_user}] FOR LOGIN [${app_user}];
IF IS_ROLEMEMBER(N'db_datareader', N'${app_user}') <> 1 ALTER ROLE db_datareader ADD MEMBER [${app_user}];
IF IS_ROLEMEMBER(N'db_datawriter', N'${app_user}') <> 1 ALTER ROLE db_datawriter ADD MEMBER [${app_user}];
"

echo "SQL Server UAT source database and application user initialized."
