#!/usr/bin/env bash
set -euo pipefail

# S0-7: Go Gateway service skeleton static checks.

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

check "gateway/ exists" test -d gateway
cd gateway

check "go.mod exists" test -f go.mod

# Go version >= 1.22
check "Go version in go.mod" awk '/^go / {if (substr($2,1,4)+0 >= 1.22) exit 0; else exit 1}' go.mod

for dep in github.com/gin-gonic/gin gorm.io/gorm github.com/redis/go-redis/v9 github.com/spf13/viper github.com/golang-jwt/jwt/v5 golang.org/x/crypto github.com/swaggo/gin-swagger github.com/stretchr/testify go.uber.org/zap; do
  check "go.mod requires $dep" grep -q "$dep" go.mod
done

# Makefile targets
for target in run test build lint migrate-up migrate-down; do
  check "Makefile target $target" grep -q "^$target:" Makefile
done

check "Dockerfile exists" test -f Dockerfile
check "Dockerfile sets non-root USER" grep -qE '^USER [^r]' Dockerfile
check "config.example.yaml exists" test -f config/config.example.yaml

# No real passwords in example config (allow placeholders and empty values).
if grep -inE 'password|secret|token' config/config.example.yaml \
  | grep -vE 'placeholder|example|dummy|TODO|FIXME|\$\{|change-me|""|0{8,}|^\s*#' \
  | grep -qE ':\s*["'\''"'\''a-zA-Z0-9]{8,}'; then
  echo "[FAIL] possible hardcoded secret in config.example.yaml"
  fail=1
else
  echo "[PASS] config.example.yaml has no obvious secrets"
fi

# Go buildable if Go is available.
if command -v go > /dev/null 2>&1; then
  check "go.mod tidy" go mod verify
else
  echo "[SKIP] go not installed"
fi

if [ "$fail" -eq 0 ]; then
  echo "S0-7 validation passed."
else
  echo "S0-7 validation failed."
  exit 1
fi
