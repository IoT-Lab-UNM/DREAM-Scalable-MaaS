#!/bin/bash
set -e

HUB_PUBLIC_IP="$1"
WG_CONF="/etc/wireguard/wg0.conf"

if [ -z "$HUB_PUBLIC_IP" ]; then
    echo "Usage: $0 <HUB_PUBLIC_IP>"
    echo "Example: $0 98.32.29.132"
    exit 1
fi

echo "Updating WireGuard endpoint to ${HUB_PUBLIC_IP}:51820"
sudo sed -i "s/^Endpoint = .*/Endpoint = ${HUB_PUBLIC_IP}:51820/" "$WG_CONF"

echo "Restarting WireGuard..."
sudo wg-quick down wg0 2>/dev/null || true
sudo ip link delete wg0 2>/dev/null || true
sudo wg-quick up wg0

echo "Done. Current WireGuard status:"
sudo wg show
