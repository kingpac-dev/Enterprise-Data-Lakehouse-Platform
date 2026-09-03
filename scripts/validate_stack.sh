#!/usr/bin/env bash
# ==============================================================================
# Platform Configuration & Compose Syntax Validator
# ==============================================================================
set -euo pipefail

echo "=== [1/3] Validating Docker Compose Syntax ==="
for file in compose/*.yml; do
  echo "Validating ${file}..."
  docker compose -f "${file}" config > /dev/null
  echo "  [PASS] ${file} is valid."
done

echo "=== [2/3] Checking for Secret Leaks ==="
if grep -rnE --exclude-dir={.git,docs} "(password|secret)[ \t]*[:=][ \t]*[a-zA-Z0-9_]{6,}" . | grep -v -E "(\$\{|\.example|change_this|admin_profile|minio_dev)"; then
  echo "  [FAIL] Potential hardcoded secret detected!"
  exit 1
else
  echo "  [PASS] No hardcoded production secrets found."
fi

echo "=== [3/3] Validating ClickHouse Config XML Syntax ==="
python -c "
import xml.etree.ElementTree as ET, glob
for f in glob.glob('clickhouse/**/*.xml', recursive=True):
    try:
        ET.parse(f)
        print(f'  [PASS] {f}')
    except Exception as e:
        print(f'  [FAIL] {f}: {e}')
        exit(1)
"

echo "=== ALL PLATFORM VALIDATIONS PASSED ==="
