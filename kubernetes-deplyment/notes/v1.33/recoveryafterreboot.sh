#!/usr/bin/env bash
set -euo pipefail

echo "========== Kubernetes post-reboot recovery =========="

echo "[1/7] Disabling swap now..."
sudo swapoff -a

echo "[2/7] Disabling swap persistently in /etc/fstab..."
sudo sed -i.bak '/\sswap\s/s/^/#/' /etc/fstab || true

echo "[3/7] Loading required kernel modules..."
sudo modprobe overlay
sudo modprobe br_netfilter

echo "[4/7] Persisting kernel modules across reboot..."
cat <<'EOF' | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

echo "[5/7] Writing Kubernetes sysctl settings..."
cat <<'EOF' | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
EOF

echo "[6/7] Applying sysctl settings and restarting services..."
sudo sysctl --system
sudo systemctl restart containerd
sudo systemctl restart kubelet

echo "[7/7] Verifying settings..."
echo "--- Swap status ---"
swapon --show || true
free -h

echo "--- Loaded modules ---"
lsmod | grep -E 'overlay|br_netfilter' || true

echo "--- Sysctl values ---"
sysctl net.bridge.bridge-nf-call-iptables
sysctl net.bridge.bridge-nf-call-ip6tables
sysctl net.ipv4.ip_forward

echo "--- Service status ---"
sudo systemctl is-active containerd
sudo systemctl is-active kubelet

echo "========== Recovery completed =========="
echo "Run this on each cluster node:"
echo "  - masternode"
echo "  - cloudnode"
echo "  - edgenode"
echo
echo "Then on the master run:"
echo "  kubectl delete pod -n kube-flannel --all"
echo "  kubectl get pods -A -o wide"