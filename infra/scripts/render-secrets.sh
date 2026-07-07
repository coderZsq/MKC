#!/bin/bash
set -e

export MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-dev-root}"
export MYSQL_PASSWORD="${MYSQL_PASSWORD:-dev-mkc}"
export MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-dev-minio}"

for f in infra/k8s/*/secret.yaml.tpl; do
  target="${f%.tpl}"
  envsubst < "$f" > "$target"
done
