#!/usr/bin/env bash
set -euo pipefail

# S0-8: Python AI Service skeleton static checks.

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

check "ai-service/ exists" test -d ai-service
cd ai-service

for f in app/__init__.py requirements.txt requirements-dev.txt Dockerfile Makefile; do
  check "$f exists" test -f "$f"
done

for dir in app/api app/services app/tasks app/core tests; do
  check "$dir/ exists" test -d "$dir"
done

for dep in Flask Celery redis pydantic-settings gunicorn gevent pytest black ruff mypy; do
  lower="$(printf '%s' "$dep" | tr '[:upper:]' '[:lower:]')"
  check "requirements contain $dep" bash -c "grep -qiE '^$lower[\[>=~<]' requirements.txt requirements-dev.txt"
done

check "Dockerfile exists" test -f Dockerfile
check "Dockerfile uses python:3.11-slim" grep -q 'python:3\.11-slim' Dockerfile
check "Dockerfile sets non-root USER" grep -qE '^USER [^r]' Dockerfile

# Makefile targets
for target in install test lint format run worker; do
  check "Makefile target $target" grep -q "^$target:" Makefile
done

# Env example no real secrets (allow common placeholders).
for env in .env.example config/.env.example; do
  if [ -f "$env" ]; then
    if grep -inE 'password|secret|token|api_key' "$env" \
      | grep -vE 'placeholder|example|dummy|TODO|FIXME|\$\{|change-me|^\s*#' \
      | grep -qE '=.+' ; then
      echo "[FAIL] possible secret in $env"
      fail=1
    else
      echo "[PASS] $env has no obvious secrets"
    fi
  fi
done

if [ "$fail" -eq 0 ]; then
  echo "S0-8 validation passed."
else
  echo "S0-8 validation failed."
  exit 1
fi
