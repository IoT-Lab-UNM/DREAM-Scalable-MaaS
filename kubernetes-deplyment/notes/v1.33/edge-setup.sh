#!/usr/bin/env bash
set -euo pipefail

echo "Checking requirements..."
uname -r
if command -v nft >/dev/null 2>&1; then
  nft --version
else
  echo "nft command not found. Install nftables first."
fi

echo "Enabling IPv4 forwarding..."
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.ipv4.ip_forward = 1
EOF
sudo sysctl --system
sysctl net.ipv4.ip_forward

echo "Disabling swap..."
sudo swapoff -a
sudo sed -i.bak '/\sswap\s/s/^/#/' /etc/fstab || true

echo "Removing conflicting packages..."
sudo apt-get remove -y docker.io docker-compose docker-compose-v2 docker-doc podman-docker containerd runc || true

echo "Installing dependencies..."
sudo apt-get update
sudo apt-get install -y ca-certificates curl gpg

echo "Adding Docker GPG key..."
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo "Adding Docker repository..."
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt-get update

echo "Installing containerd..."
sudo apt-get install -y containerd.io

echo "Configuring containerd..."
sudo mkdir -p /etc/containerd
sudo containerd config default | sudo tee /etc/containerd/config.toml > /dev/null
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml

echo "Restarting containerd..."
sudo systemctl restart containerd
sudo systemctl enable containerd
sudo systemctl status containerd --no-pager || true

echo "Done."
echo "Next: continue with KubeEdge setup on this edge node."