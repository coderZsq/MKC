#!/bin/bash
set -e

NAMESPACE="mkc-dev"

echo "Port-forwarding local services..."
kubectl port-forward -n "$NAMESPACE" svc/mysql 3306:3306 &
kubectl port-forward -n "$NAMESPACE" svc/redis 6379:6379 &
kubectl port-forward -n "$NAMESPACE" svc/minio 9000:9000 9001:9001 &
kubectl port-forward -n "$NAMESPACE" svc/jaeger 16686:16686 &

wait
