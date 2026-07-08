#!/usr/bin/env bash
set -euo pipefail

# S0-1: Repository governance static checks.

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

check "README.md exists" test -f README.md
check "LICENSE exists" test -f LICENSE
check ".gitignore exists" test -f .gitignore
check "client/ directory exists" test -d client
check "gateway/ directory exists" test -d gateway
check "ai-service/ directory exists" test -d ai-service
check "infra/ directory exists" test -d infra
check "docs/ directory exists" test -d docs
check ".github/workflows/ exists" test -d .github/workflows
check ".github/ISSUE_TEMPLATE/ exists" test -d .github/ISSUE_TEMPLATE
check ".github/PULL_REQUEST_TEMPLATE.md exists" test -f .github/PULL_REQUEST_TEMPLATE.md

# .gitignore must ignore secrets
check ".gitignore ignores .env" git check-ignore -q .env
check ".gitignore ignores *.secret.yaml" git check-ignore -q foo.secret.yaml

# Report current branch (informational only — validation may run on main or a feature branch).
echo "[INFO] current branch: $(git branch --show-current 2>/dev/null || git rev-parse --abbrev-ref HEAD)"

# First commits mention repository/project initialization.
check "first commits mention project init" bash -c 'git log --reverse --format=%s | head -n 3 | grep -qiE "init(ial)? (commit|repo|project)"'

# No hardcoded passwords/keys in source code.
# This is a heuristic: flag lines that look like real secrets.
if grep -RinE \
  '(password|secret|token|api_key)\s*[:=]\s*["'\''"'\''a-zA-Z0-9]{8,}' \
  gateway/ ai-service/ \
  --include='*.go' --include='*.py' \
  --exclude-dir=.venv --exclude-dir=venv --exclude-dir=node_modules --exclude-dir=vendor \
  | grep -vE '(settings\.|os\.getenv|getenv|os\.LookupEnv|viper|placeholder|example|dummy|test-|test_)' \
  | grep -vE '"\$\{|env\.|TODO|FIXME' ; then
  echo "[FAIL] possible hardcoded secret found in source"
  fail=1
else
  echo "[PASS] no obvious hardcoded secrets in source"
fi

if [ "$fail" -eq 0 ]; then
  echo "S0-1 validation passed."
else
  echo "S0-1 validation failed."
  exit 1
fi
