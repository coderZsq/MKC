#!/bin/bash
set -e

NAMESPACE="mkc-dev"

echo "Starting port-forwards in background..."
echo "Press Ctrl+C to stop all forwards."
echo

kubectl port-forward -n "$NAMESPACE" svc/mysql 3306:3306 &
kubectl port-forward -n "$NAMESPACE" svc/redis 6379:6379 &
kubectl port-forward -n "$NAMESPACE" svc/minio 9000:9000 9001:9001 &
kubectl port-forward -n "$NAMESPACE" svc/jaeger 16686:16686 &
kubectl port-forward -n "$NAMESPACE" svc/milvus 19530:19530 &

echo "Port-forwards started:"
echo "  MySQL:     localhost:3306"
echo "  Redis:     localhost:6379"
echo "  MinIO S3:  localhost:9000"
echo "  MinIO UI:  localhost:9001"
echo "  Jaeger UI: localhost:16686"
echo "  Milvus:    localhost:19530"
echo

wait
