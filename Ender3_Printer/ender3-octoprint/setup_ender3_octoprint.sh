#!/bin/bash
set -euo pipefail

IMAGE="henok28/ender3-octoprint-client:v1.0"
NAMESPACE="microservices"

kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

echo "[1/5] Build Docker image"
docker build -t "$IMAGE" .

echo "[2/5] Push Docker image"
docker push "$IMAGE"

echo "[3/5] Create/update OctoPrint Secret from local environment"
if [ -z "${OCTOPRINT_API_KEY:-}" ]; then
  echo "ERROR: Please export OCTOPRINT_API_KEY before running this script."
  echo "Example: export OCTOPRINT_API_KEY='your_key_here'"
  exit 1
fi

kubectl -n "$NAMESPACE" create secret generic octoprint-credentials \
  --from-literal=OCTOPRINT_API_KEY="$OCTOPRINT_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "[4/5] Apply ConfigMap"
kubectl apply -f octoprint-configmap.yaml

echo "[5/5] Start one-shot Kubernetes Job"
kubectl delete job ender3-octoprint-print-job -n "$NAMESPACE" --ignore-not-found=true
kubectl apply -f octoprint-print-job.yaml

kubectl -n "$NAMESPACE" get pods -l app=ender3-octoprint-client -o wide

echo "\nFollow logs with:"
echo "kubectl -n $NAMESPACE logs -f job/ender3-octoprint-print-job"
