#!/usr/bin/env bash
set -euo pipefail

OVERLAY="${1:-prod}"
NAMESPACE="${NAMESPACE:-mkc}"
KUSTOMIZE_DIR="infra/k8s/overlays/${OVERLAY}"

if [[ ! -d "$KUSTOMIZE_DIR" ]]; then
  echo "Unknown overlay: $OVERLAY" >&2
  echo "Usage: $0 [local|prod]" >&2
  exit 2
fi

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required" >&2
  exit 2
fi

echo "Rendering ${KUSTOMIZE_DIR}..."
kubectl kustomize "$KUSTOMIZE_DIR" >/tmp/mkc-${OVERLAY}.yaml

echo "Applying ${OVERLAY} overlay..."
kubectl apply -k "$KUSTOMIZE_DIR"

echo "Waiting for core rollouts in namespace ${NAMESPACE}..."
kubectl rollout status deployment/gateway -n "$NAMESPACE" --timeout=300s
kubectl rollout status deployment/ai-service -n "$NAMESPACE" --timeout=300s
kubectl rollout status deployment/ai-worker -n "$NAMESPACE" --timeout=300s
kubectl rollout status deployment/client -n "$NAMESPACE" --timeout=300s
kubectl rollout status statefulset/mysql -n "$NAMESPACE" --timeout=300s
kubectl rollout status statefulset/redis -n "$NAMESPACE" --timeout=300s
kubectl rollout status statefulset/milvus-etcd -n "$NAMESPACE" --timeout=300s
kubectl rollout status statefulset/milvus -n "$NAMESPACE" --timeout=600s

echo "Deployment complete."
