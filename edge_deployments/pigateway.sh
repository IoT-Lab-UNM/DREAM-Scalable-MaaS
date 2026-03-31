#!/usr/bin/env bash
set -euo pipefail

KUBEEDGE_VERSION="v1.23.0"
CLOUDNODE_IP="10.12.10.124"
TOKEN="e84aa4f079426b66718898f74c0490c6422d0e1099b68e331893f9f78dc34238.eyJhbGciOiJIUzI1NLIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NzUwNjg2NjR9.K4cgBXOvkcRgn71eq1Pb6wbTzu3moONswu3t9Z632Vc"

echo "=== Installing keadm on pigateway ==="
wget -q https://github.com/kubeedge/kubeedge/releases/download/${KUBEEDGE_VERSION}/keadm-${KUBEEDGE_VERSION}-linux-arm64.tar.gz
tar -zxf keadm-${KUBEEDGE_VERSION}-linux-arm64.tar.gz
sudo cp keadm-${KUBEEDGE_VERSION}-linux-arm64/keadm/keadm /usr/local/bin/keadm
keadm version || true

echo "=== Joining pigateway to CloudCore ==="
sudo keadm join \
  --cloudcore-ipport="${CLOUDNODE_IP}:10000" \
  --token="${TOKEN}" \
  --remote-runtime-endpoint=unix:///run/containerd/containerd.sock \
  --cgroupdriver=systemd \
  --kubeedge-version="${KUBEEDGE_VERSION}"
  

echo "=== EdgeCore service status ==="
sudo systemctl status edgecore --no-pager || true