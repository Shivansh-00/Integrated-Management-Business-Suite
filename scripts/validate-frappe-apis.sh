#!/usr/bin/env bash
set -euo pipefail

: "${BASE_URL:=http://localhost:8000}"

curl -fsS "$BASE_URL/api/method/ping" >/dev/null
curl -fsS "$BASE_URL/api/method/ibms_core.api.graphql_api.get_schema" >/dev/null

echo "Frappe API smoke checks passed against $BASE_URL"
