#!/bin/bash
set -e

export MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-dev-root}"
export MYSQL_PASSWORD="${MYSQL_PASSWORD:-dev-mkc}"
export REDIS_PASSWORD="${REDIS_PASSWORD:-dev-redis}"
export MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-dev-minio}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

for f in "$REPO_ROOT"/infra/k8s/*/secret.yaml.tpl; do
  target="${f%.tpl}"
  if command -v envsubst >/dev/null 2>&1; then
    envsubst < "$f" > "$target"
  else
    python3 -c 'import os, sys; sys.stdout.write(os.path.expandvars(sys.stdin.read()))' < "$f" > "$target"
  fi
done

echo "Rendered secrets:"
find "$REPO_ROOT/infra/k8s" -name "secret.yaml" -print
