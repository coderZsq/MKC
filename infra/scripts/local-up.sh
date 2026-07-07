#!/bin/bash
set -e

NAMESPACE="mkc-dev"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=== MKC Local Kubernetes Environment ==="
echo

echo "[1/8] Checking Docker Desktop Kubernetes..."
if ! kubectl get nodes >/dev/null 2>&1; then
  echo "Error: Docker Desktop Kubernetes is not enabled or kubectl cannot connect."
  echo "Please enable Kubernetes in Docker Desktop settings."
  exit 1
fi
kubectl get nodes

echo
echo "[2/8] Installing nginx-ingress-controller..."
kubectl apply -f "$REPO_ROOT/infra/k8s/nginx-ingress/ingress-nginx.yaml"
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=180s

echo
echo "[3/8] Creating namespace..."
kubectl apply -f "$REPO_ROOT/infra/k8s/namespaces/mkc-dev.yaml"

echo
echo "[4/8] Rendering secrets..."
"$REPO_ROOT/infra/scripts/render-secrets.sh"

echo
echo "[5/8] Applying manifests..."
kubectl apply -f "$REPO_ROOT/infra/k8s/mysql/"
kubectl apply -f "$REPO_ROOT/infra/k8s/redis/"
kubectl apply -f "$REPO_ROOT/infra/k8s/minio/"
kubectl apply -f "$REPO_ROOT/infra/k8s/milvus/"
kubectl apply -f "$REPO_ROOT/infra/k8s/jaeger/"
kubectl apply -f "$REPO_ROOT/infra/k8s/gateway/"

echo
echo "[6/8] Waiting for MinIO bucket initialization job..."
kubectl wait --for=condition=complete job/minio-init-buckets -n "$NAMESPACE" --timeout=300s

echo
echo "[7/8] Waiting for infrastructure pods..."
kubectl wait --for=condition=ready pod -l app=mysql -n "$NAMESPACE" --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n "$NAMESPACE" --timeout=300s
kubectl wait --for=condition=ready pod -l app=minio -n "$NAMESPACE" --timeout=300s
kubectl wait --for=condition=ready pod -l app=jaeger -n "$NAMESPACE" --timeout=300s
kubectl wait --for=condition=ready pod -l app=milvus-etcd -n "$NAMESPACE" --timeout=300s
kubectl wait --for=condition=ready pod -l app=milvus -n "$NAMESPACE" --timeout=600s

echo
echo "[8/8] Done!"
echo
echo "Add the following lines to /etc/hosts:"
echo "  127.0.0.1 mkc.local"
echo "  127.0.0.1 minio.mkc.local"
echo "  127.0.0.1 jaeger.mkc.local"
echo
echo "Useful commands:"
echo "  kubectl get pods -n $NAMESPACE"
echo "  ./infra/scripts/port-forward.sh"
