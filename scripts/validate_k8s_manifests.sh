#!/usr/bin/env bash
set -euo pipefail

LOCAL_OUT="${LOCAL_OUT:-/tmp/mkc-local.yaml}"
PROD_OUT="${PROD_OUT:-/tmp/mkc-prod.yaml}"

require() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "$1 is required" >&2
    exit 2
  fi
}

contains() {
  local file="$1"
  local pattern="$2"
  local message="$3"
  if ! grep -Eq "$pattern" "$file"; then
    echo "Missing: $message" >&2
    exit 1
  fi
}

require kubectl

kubectl kustomize infra/k8s/overlays/local >"$LOCAL_OUT"
kubectl kustomize infra/k8s/overlays/prod >"$PROD_OUT"

contains "$PROD_OUT" "kind: Ingress" "prod Ingress"
contains "$PROD_OUT" "host: mkc.example.com" "prod domain placeholder"
contains "$PROD_OUT" "cert-manager.io/cluster-issuer: letsencrypt-prod" "cert-manager issuer annotation"
contains "$PROD_OUT" "secretName: mkc-tls" "TLS secret"
contains "$PROD_OUT" "nginx.ingress.kubernetes.io/proxy-buffering: \"off\"" "SSE proxy buffering disabled"
contains "$PROD_OUT" "kind: ClusterIssuer" "cert-manager ClusterIssuer"

contains "$PROD_OUT" "name: gateway" "Gateway workload"
contains "$PROD_OUT" "name: ai-service" "AI Service workload"
contains "$PROD_OUT" "name: ai-worker" "AI worker workload"
contains "$PROD_OUT" "name: client" "Client workload"

contains "$PROD_OUT" "readinessProbe:" "readiness probes"
contains "$PROD_OUT" "livenessProbe:" "liveness probes"
contains "$PROD_OUT" "resources:" "resource requests and limits"
contains "$PROD_OUT" "volumeClaimTemplates:" "StatefulSet persistence"
contains "$PROD_OUT" "kind: PersistentVolumeClaim" "MinIO persistence"
contains "$PROD_OUT" "secretKeyRef:" "Secret references"

if grep -Eq "(dev-jwt-secret|dev-internal-key|dev-minio|dev-redis|dev-mkc)" "$PROD_OUT"; then
  echo "Prod render contains development secret placeholder" >&2
  exit 1
fi

echo "Kubernetes manifests validated."
