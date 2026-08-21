#!/usr/bin/env sh
set -eu

IMAGE="${POLICY_IMAGE:-henok28/dream-policy-management:0.1.0}"

docker build --no-cache -t "$IMAGE" .
docker push "$IMAGE"

printf '%s\n' \
  "Image pushed: $IMAGE" \
  "Deploy from masternode with:" \
  "kubectl apply -f policy-management-system/policy_manager_deployment.yaml"
