#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-web-order-app:latest}"
NAMESPACE="${NAMESPACE:-maas}"
DEPLOYMENT_YAML="${DEPLOYMENT_YAML:-web-order-app-deployment.yaml}"

echo "[1/5] Building image: ${IMAGE_NAME}"

if command -v docker >/dev/null 2>&1; then
  docker build -t "${IMAGE_NAME}" .
elif command -v nerdctl >/dev/null 2>&1; then
  nerdctl build -t "${IMAGE_NAME}" .
else
  echo "ERROR: docker or nerdctl is required to build the image."
  exit 1
fi

echo "[2/5] Creating namespace if needed"
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

echo "[3/5] Applying Kubernetes manifests"
kubectl apply -f "${DEPLOYMENT_YAML}"

echo "[4/5] Waiting for rollout"
kubectl rollout status deployment/web-order-app -n "${NAMESPACE}" --timeout=180s

echo "[5/5] Deployment summary"
kubectl get pods -n "${NAMESPACE}" -o wide
kubectl get svc web-order-app -n "${NAMESPACE}"

echo
echo "Access URL from your LAN:"
echo "  http://<cloudnode-ip>:30080"
echo
echo "Health check:"
echo "  curl http://<cloudnode-ip>:30080/api/health"
