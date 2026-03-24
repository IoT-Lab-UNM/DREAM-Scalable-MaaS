#!/usr/bin/env bash
set -euo pipefail

echo "========== Kubernetes node base setup (master/worker) =========="

echo "[1/10] Checking OS/kernel..."
uname -r
if command -v nft >/dev/null 2>&1; then
  nft --version
else
  echo "nft command not found. Continuing..."
fi

echo "[2/10] Disabling swap..."
sudo swapoff -a
sudo sed -i.bak '/\sswap\s/s/^/#/' /etc/fstab || true

echo "[3/10] Loading required kernel modules..."
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter

echo "[4/10] Applying Kubernetes sysctl settings..."
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
EOF

sudo sysctl --system

echo "[5/10] Verifying kernel/network settings..."
lsmod | grep -E 'overlay|br_netfilter' || true
sysctl net.bridge.bridge-nf-call-iptables
sysctl net.bridge.bridge-nf-call-ip6tables
sysctl net.ipv4.ip_forward

echo "[6/10] Removing conflicting packages..."
sudo apt-get remove -y docker.io docker-compose docker-compose-v2 docker-doc podman-docker containerd runc || true

echo "[7/10] Installing base dependencies..."
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gpg

echo "[8/10] Adding Docker repository for containerd..."
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt-get update

echo "[9/10] Installing and configuring containerd..."
sudo apt-get install -y containerd.io

sudo mkdir -p /etc/containerd
sudo containerd config default | sudo tee /etc/containerd/config.toml > /dev/null
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml

sudo systemctl daemon-reload
sudo systemctl enable containerd
sudo systemctl restart containerd

echo "[10/10] Installing kubelet, kubeadm, kubectl..."
sudo mkdir -p -m 755 /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.33/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.33/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list

sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl

sudo systemctl enable kubelet
sudo systemctl restart kubelet

echo "========== Setup completed successfully =========="
echo "Next:"
echo "  - On the master: run kubeadm init ..."
echo "  - On workers: run the kubeadm join command from the master"