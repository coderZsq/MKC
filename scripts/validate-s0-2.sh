#!/usr/bin/env bash
set -euo pipefail

# S0-2: Local K8s environment static checks.

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

check "local-up.sh exists" test -x infra/scripts/local-up.sh
check "local-down.sh exists" test -x infra/scripts/local-down.sh
check "render-secrets.sh exists" test -x infra/scripts/render-secrets.sh
check "port-forward.sh exists" test -x infra/scripts/port-forward.sh

# Secret templates use placeholders, not real values.
check "mysql secret template uses placeholder" grep -q '\${MYSQL_ROOT_PASSWORD}' infra/k8s/mysql/secret.yaml.tpl
check "redis secret template uses placeholder" grep -q '\${REDIS_PASSWORD}' infra/k8s/redis/secret.yaml.tpl

# Generated secrets are ignored.
check "mysql secret.yaml is ignored" git check-ignore -q infra/k8s/mysql/secret.yaml
check "redis secret.yaml is ignored" git check-ignore -q infra/k8s/redis/secret.yaml

# YAML dry-run validation if kubectl is available.
if command -v kubectl > /dev/null 2>&1; then
  for f in infra/k8s/**/*.yaml; do
    if [ -f "$f" ]; then
      if kubectl apply --dry-run=client -f "$f" > /dev/null 2>&1; then
        echo "[PASS] kubectl dry-run: $f"
      else
        echo "[FAIL] kubectl dry-run: $f"
        fail=1
      fi
    fi
  done
else
  echo "[SKIP] kubectl not available, skipping YAML dry-run validation"
fi

# Image source uses DaoCloud mirror.
check "K8s manifests use DaoCloud mirror" grep -Rq 'm\.daocloud\.io' infra/k8s/

if [ "$fail" -eq 0 ]; then
  echo "S0-2 validation passed."
else
  echo "S0-2 validation failed."
  exit 1
fi
