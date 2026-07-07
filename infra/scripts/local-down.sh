#!/bin/bash
set -e

NAMESPACE="mkc-dev"

echo "Deleting namespace resources..."
kubectl delete namespace "$NAMESPACE" --ignore-not-found=true

echo "Deleting nginx-ingress-controller..."
kubectl delete namespace ingress-nginx --ignore-not-found=true

echo "Note: Docker Desktop Kubernetes cluster itself is kept running."
echo "To fully disable, use Docker Desktop settings."
