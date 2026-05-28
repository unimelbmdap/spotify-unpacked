#!/usr/bin/env bash
# End-to-end smoke against a running backend (default: http://localhost:8000).
# Requires: curl, jq.
set -euo pipefail

BASE="${BASE:-http://localhost:8000}"
ADMIN_USER="${ADMIN_USERNAME:-admin}"
ADMIN_PASS="${ADMIN_PASSWORD:?set ADMIN_PASSWORD or source .env}"

echo "▶ health"
curl -sfS "$BASE/api/health" | jq .

echo "▶ create one code"
CODE=$(curl -sfS \
  -u "$ADMIN_USER:$ADMIN_PASS" \
  -H 'Content-Type: application/json' \
  -H 'X-Admin-Request: 1' \
  -d '{"count":1,"max_uses":1,"admin_label":"smoke"}' \
  "$BASE/api/admin/codes" | jq -r '.[0].code')
echo "  issued: $CODE"

echo "▶ donate"
curl -sfS -X POST \
  -F "participant_code=$CODE" \
  -F "consent_version=v1.0" \
  -F "consent_accepted=true" \
  -F "app_version=smoke" \
  -F "files=@scripts/sample_data/StreamingHistory.json" \
  "$BASE/api/donate" | jq .

echo "▶ list donations for this code"
curl -sfS \
  -u "$ADMIN_USER:$ADMIN_PASS" \
  -H 'X-Admin-Request: 1' \
  "$BASE/api/admin/donations?code=$CODE" | jq .

echo "▶ retry should fail (code exhausted)"
HTTP_CODE=$(curl -sS -o /dev/null -w '%{http_code}' -X POST \
  -F "participant_code=$CODE" \
  -F "consent_version=v1.0" \
  -F "consent_accepted=true" \
  -F "app_version=smoke" \
  -F "files=@scripts/sample_data/StreamingHistory.json" \
  "$BASE/api/donate")
test "$HTTP_CODE" = "401"
echo "  got expected 401"
