#!/usr/bin/env bash
set -euo pipefail

# S0-5: API design static checks.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

fail=0

check() {
  local msg="$1"
  shift
  if "$@" > /dev/null 2>&1; then
    echo "[PASS] $msg"
  else
    echo "[FAIL] $msg"
    fail=1
  fi
}

check "openapi.yaml exists" test -f docs/api/openapi.yaml
check "openapi.yaml uses 3.0.3" grep -q 'openapi: 3\.0\.3' docs/api/openapi.yaml

for endpoint in /auth/register /auth/login /auth/refresh /auth/logout /files/upload /tasks /tasks/{task_id} /tasks/{task_id}/progress; do
  # Use sed to escape braces for grep
  pattern="$(printf '%s' "$endpoint" | sed 's/{/\\{/g; s/}/\\}/g')"
  check "endpoint $endpoint defined" bash -c "grep -qE '^  ['\"']?$pattern['\"']?' docs/api/openapi.yaml"
done

check "Envelope schema has success" bash -c "grep -q 'Envelope:' docs/api/openapi.yaml && grep -A 15 'Envelope:' docs/api/openapi.yaml | grep -q 'success:'"
check "Envelope schema has data" bash -c "grep -A 15 'Envelope:' docs/api/openapi.yaml | grep -q 'data:'"
check "Envelope schema has error" bash -c "grep -A 15 'Envelope:' docs/api/openapi.yaml | grep -q 'error:'"
check "Envelope schema has meta" bash -c "grep -A 15 'Envelope:' docs/api/openapi.yaml | grep -q 'meta:'"

check "bearerAuth security scheme" bash -c "grep -q 'bearerAuth:' docs/api/openapi.yaml"
check "expires_in default/example 900" bash -c "grep -A 3 'expires_in:' docs/api/openapi.yaml | grep -qE 'default:|example:\\s*900'"

# Validate spec if openapi-spec-validator is installed.
if command -v openapi-spec-validator > /dev/null 2>&1; then
  check "openapi.yaml validates" openapi-spec-validator docs/api/openapi.yaml
else
  echo "[SKIP] openapi-spec-validator not installed"
fi

if [ "$fail" -eq 0 ]; then
  echo "S0-5 validation passed."
else
  echo "S0-5 validation failed."
  exit 1
fi
