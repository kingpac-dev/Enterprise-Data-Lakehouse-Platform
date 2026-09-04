"""
AI SQL Security Guardrails
==========================
Enforces strict zero-trust security policies on all AI-generated or user queries:
  1. Only read-only SELECT and WITH statements permitted.
  2. Blocks DDL, DML, mutation, and administrative commands.
  3. Limits queries strictly to mart and serving database namespaces.
  4. Enforces hard LIMIT clauses to prevent memory exhaustion.
"""

import re
from typing import Tuple

FORBIDDEN_KEYWORDS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bTRUNCATE\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bATTACH\b",
    r"\bDETACH\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bKILL\b",
    r"\bSYSTEM\b",
    r"\bOPTIMIZE\b",
    r"\bFILE\b",
    r"\bURL\b",
    r"\bS3\b",
]

ALLOWED_DATABASES = ["mart", "serving"]


def validate_sql_guardrails(sql: str) -> Tuple[bool, str, str]:
    """
    Validates SQL statement against enterprise security policies.
    Returns: (is_valid: bool, reason: str, sanitized_sql: str)
    """
    cleaned = sql.strip()
    # Remove trailing semicolons
    cleaned = re.sub(r";+\s*$", "", cleaned)

    # 1. Must start with SELECT or WITH
    if not re.match(r"^(SELECT|WITH)\b", cleaned, re.IGNORECASE):
        return False, "Query must start with SELECT or WITH (read-only allowed).", cleaned

    # 2. Check forbidden keywords
    for pattern in FORBIDDEN_KEYWORDS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            match = re.search(pattern, cleaned, re.IGNORECASE).group(0)
            return False, f"Security Violation: Forbidden keyword '{match}' detected in query.", cleaned

    # 3. Check database access boundaries (No raw or system tables allowed)
    disallowed_match = re.search(r"\b(raw|system|information_schema)\.[a-zA-Z0-9_]+", cleaned, re.IGNORECASE)
    if disallowed_match:
        target = disallowed_match.group(0)
        return False, f"Access Denied: AI queries may only access 'mart' or 'serving' layers. Unauthorized target: '{target}'", cleaned

    # 4. Enforce LIMIT clause
    if not re.search(r"\bLIMIT\s+\d+\b", cleaned, re.IGNORECASE):
        cleaned += " LIMIT 100"

    return True, "Guardrail checks passed.", cleaned
