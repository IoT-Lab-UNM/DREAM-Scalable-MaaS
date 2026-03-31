#!/usr/bin/env bash
set -euo pipefail

KUBEEDGE_VERSION="v1.23.0"
CLOUDNODE_IP="10.12.10.124"

echo "=== Installing keadm on masternode ==="
wget -q https://github.com/kubeedge/kubeedge/releases/download/${KUBEEDGE_VERSION}/keadm-${KUBEEDGE_VERSION}-linux-amd64.tar.gz
tar -zxf keadm-${KUBEEDGE_VERSION}-linux-amd64.tar.gz
sudo cp keadm-${KUBEEDGE_VERSION}-linux-amd64/keadm/keadm /usr/local/bin/keadm
keadm version || true

echo "=== Ensuring cloudnode label exists ==="
kubectl label node cloudnode kubeedge-role=cloud --overwrite

echo "=== Initializing CloudCore into the cluster ==="
sudo keadm init \
  --advertise-address="${CLOUDNODE_IP}" \
  --kube-config=/etc/kubernetes/admin.conf \
  --kubeedge-version="${KUBEEDGE_VERSION}" \
  --set cloudCore.nodeSelector."kubeedge-role"=cloud

echo "=== Waiting briefly, then showing CloudCore pod placement ==="
sleep 10
kubectl get pods -n kubeedge -o wide || true

echo "=== Getting token for the Pi join step ==="
sudo keadm gettoken