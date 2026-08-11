#!/usr/bin/env bash
set -euo pipefail

KUBEEDGE_VERSION="v1.23.0"
CLOUDNODE_IP="10.12.10.124"
TOKEN="e84aa4f079426b66718898f74c0490c6422d0e1099b68e331893f9f78dc34238.eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODY0OTQ0MTV9.OaFG6nV0-BrOchjoOiWBKBBffnXzuHWbLuqrK8R54TM"

EDGE_NODE_NAME="$(hostname)"
CRI_ENDPOINT="unix:///run/containerd/containerd.sock"

echo "=== EdgeCore join setup for ${EDGE_NODE_NAME} ==="

echo "=== Verifying containerd runtime prepared by the runtime script ==="
sudo mkdir -p /etc/containerd

if [[ ! -f /etc/containerd/config.toml ]]; then
  echo "ERROR: /etc/containerd/config.toml not found."
  echo "Run the runtime setup script first."
  exit 1
fi

grep "SystemdCgroup" /etc/containerd/config.toml || true

sudo systemctl daemon-reload
sudo systemctl enable containerd
sudo systemctl restart containerd
sudo systemctl status containerd --no-pager || true

echo "=== Verifying containerd CRI plugin ==="
sudo ctr plugins ls | grep -i cri || true

if [[ ! -S /run/containerd/containerd.sock ]]; then
  echo "ERROR: containerd socket /run/containerd/containerd.sock not found."
  exit 1
fi

echo "=== Checking CloudCore reachability ==="
if command -v nc >/dev/null 2>&1; then
  nc -zv "${CLOUDNODE_IP}" 10000
else
  echo "nc not installed; skipping TCP port test."
fi

echo "=== Cleaning previous KubeEdge edge state if present ==="
if command -v keadm >/dev/null 2>&1; then
  sudo keadm reset edge || true
fi

sudo systemctl stop edgecore 2>/dev/null || true
sudo rm -rf \
  /etc/kubeedge \
  /var/lib/kubeedge \
  /etc/systemd/system/edgecore.service.d \
  2>/dev/null || true
sudo systemctl daemon-reload

echo "=== Downloading and installing keadm ${KUBEEDGE_VERSION} for ARM64 ==="
ARCH="$(uname -m)"
if [[ "${ARCH}" != "aarch64" && "${ARCH}" != "arm64" ]]; then
  echo "ERROR: This script expects an ARM64 Raspberry Pi, but detected: ${ARCH}"
  exit 1
fi

KEADM_TARBALL="keadm-${KUBEEDGE_VERSION}-linux-arm64.tar.gz"
KEADM_DIR="keadm-${KUBEEDGE_VERSION}-linux-arm64"
KEADM_URL="https://github.com/kubeedge/kubeedge/releases/download/${KUBEEDGE_VERSION}/${KEADM_TARBALL}"

rm -rf "${KEADM_DIR}" "${KEADM_TARBALL}"

wget -q --show-progress "${KEADM_URL}" -O "${KEADM_TARBALL}"
tar -zxf "${KEADM_TARBALL}"

sudo cp "${KEADM_DIR}/keadm/keadm" /usr/local/bin/keadm
sudo chmod +x /usr/local/bin/keadm

echo "=== Verifying keadm installation ==="
command -v keadm
keadm version || true

echo "=== Joining ${EDGE_NODE_NAME} to CloudCore ==="
sudo keadm join \
  --cloudcore-ipport="${CLOUDNODE_IP}:10000" \
  --token="${TOKEN}" \
  --edgenode-name="${EDGE_NODE_NAME}" \
  --remote-runtime-endpoint="${CRI_ENDPOINT}" \
  --cgroupdriver=systemd \
  --kubeedge-version="${KUBEEDGE_VERSION}"

echo "=== Enabling and restarting EdgeCore ==="
sudo systemctl daemon-reload
sudo systemctl enable edgecore
sudo systemctl restart edgecore

sleep 5

echo "=== EdgeCore service status ==="
sudo systemctl status edgecore --no-pager || true

echo "=== Recent EdgeCore logs ==="
sudo journalctl -u edgecore.service -n 60 --no-pager || true

echo "=== EdgeCore join completed for ${EDGE_NODE_NAME} ==="
echo "Now verify from the Kubernetes master:"
echo "  kubectl get nodes -o wide"