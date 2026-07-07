#!/bin/bash
set -e

NAMESPACE="mkc-dev"

echo "Checking Docker Desktop Kubernetes..."
if ! kubectl get nodes >/dev/null 2>&1; then
  echo "Error: Docker Desktop Kubernetes is not enabled or kubectl cannot connect."
  echo "Please enable Kubernetes in Docker Desktop settings."
  exit 1
fi

echo "Creating namespace..."
kubectl apply -f infra/k8s/namespaces/mkc-dev.yaml

echo "Rendering secrets..."
./infra/scripts/render-secrets.sh

echo "Applying manifests..."
kubectl apply -f infra/k8s/mysql/
kubectl apply -f infra/k8s/redis/
kubectl apply -f infra/k8s/minio/
kubectl apply -f infra/k8s/milvus/
kubectl apply -f infra/k8s/jaeger/

echo "Waiting for pods..."
kubectl wait --for=condition=ready pod -l app=mysql -n "$NAMESPACE" --timeout=300s || true
kubectl wait --for=condition=ready pod -l app=redis -n "$NAMESPACE" --timeout=300s || true
kubectl wait --for=condition=ready pod -l app=minio -n "$NAMESPACE" --timeout=300s || true

echo "Done! Add the following lines to /etc/hosts:"
echo "127.0.0.1 mkc.local"
echo "127.0.0.1 minio.mkc.local"
echo "127.0.0.1 jaeger.mkc.local"
