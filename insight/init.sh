#!/usr/bin/env bash
set -euo pipefail

# Migrations mutate the metadata schema; snapshot and review before upgrades.
superset db upgrade
superset init
python /app/kingpac/create_admin.py
