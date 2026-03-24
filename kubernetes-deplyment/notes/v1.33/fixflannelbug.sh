#!/usr/bin/env bash
sudo modprobe overlay
sudo modprobe br_netfilter

cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
EOF

sudo sysctl --system
sudo systemctl restart containerd
sudo systemctl restart kubelet

# Then on the master:
    # kubectl delete pod -n kube-flannel --all
    # kubectl get pods -n kube-flannel -w