#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-https://mkc.example.com}"
API_BASE_URL="${API_BASE_URL:-${BASE_URL}/api/v1}"
NAMESPACE="${NAMESPACE:-mkc}"
SMOKE_EMAIL="${SMOKE_EMAIL:-smoke-$(date +%s)@example.com}"
SMOKE_PASSWORD="${SMOKE_PASSWORD:-SmokePass123!}"
UPLOAD_FILE="${UPLOAD_FILE:-}"

require() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "$1 is required" >&2
    exit 2
  fi
}

json_value() {
  python3 - "$1" "$2" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
path = sys.argv[2].split(".")
value = payload
for key in path:
    value = value[key]
print(value)
PY
}

require curl
require python3
require kubectl

echo "Checking Gateway health at ${API_BASE_URL}/health..."
curl -fsS "${API_BASE_URL}/health" >/tmp/mkc-health.json

echo "Checking Client entrypoint at ${BASE_URL}/..."
curl -fsSI "${BASE_URL}/" >/dev/null

echo "Registering smoke user ${SMOKE_EMAIL}..."
REGISTER_BODY=$(printf '{"email":"%s","password":"%s"}' "$SMOKE_EMAIL" "$SMOKE_PASSWORD")
curl -fsS -X POST "${API_BASE_URL}/auth/register" \
  -H 'Content-Type: application/json' \
  -d "$REGISTER_BODY" >/tmp/mkc-register.json

echo "Logging in smoke user..."
LOGIN_RESPONSE=$(curl -fsS -X POST "${API_BASE_URL}/auth/login" \
  -H 'Content-Type: application/json' \
  -d "$REGISTER_BODY")
ACCESS_TOKEN=$(json_value "$LOGIN_RESPONSE" "data.access_token")

if [[ -z "$ACCESS_TOKEN" ]]; then
  echo "Login did not return access token" >&2
  exit 1
fi

if [[ -n "$UPLOAD_FILE" ]]; then
  echo "Uploading smoke file ${UPLOAD_FILE}..."
  curl -fsS -X POST "${API_BASE_URL}/files/upload" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -F "file=@${UPLOAD_FILE}" >/tmp/mkc-upload.json
else
  echo "UPLOAD_FILE not set; skipping upload step."
fi

echo "Checking task list endpoint..."
curl -fsS "${API_BASE_URL}/tasks?page=1&limit=1" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" >/tmp/mkc-tasks.json

echo "Checking AI Service internal health from the cluster..."
kubectl run mkc-ai-health-smoke \
  -n "$NAMESPACE" \
  --rm \
  -i \
  --restart=Never \
  --image=curlimages/curl:8.8.0 \
  --command -- curl -fsS http://ai-service:5000/api/v1/health >/tmp/mkc-ai-health.json

echo "Smoke test passed."
