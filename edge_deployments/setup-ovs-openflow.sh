#!/bin/bash

# === CONFIGURATION ===
BRIDGE_NAME="br0"
CONTROLLER_IP="10.12.10.124"   # Update if ONOS runs elsewhere
CONTROLLER_PORT="6653"
DPID_HEX="0000000000000001"
PROTOCOL="OpenFlow13"
VETH0="veth0"
VETH1="veth1"

echo "🚧 Cleaning up previous OVS config..."
sudo ovs-vsctl del-controller $BRIDGE_NAME || true
sudo ovs-vsctl del-br $BRIDGE_NAME || true

echo "✅ Creating bridge $BRIDGE_NAME..."
sudo ovs-vsctl add-br $BRIDGE_NAME
sudo ovs-vsctl set bridge $BRIDGE_NAME other-config:datapath-id=$DPID_HEX
sudo ovs-vsctl set bridge $BRIDGE_NAME protocols=$PROTOCOL
sudo ip link set $BRIDGE_NAME up

echo "🔌 Creating dummy ports $VETH0 and $VETH1..."
sudo ip link add $VETH0 type veth peer name $VETH1 || true
sudo ip link set $VETH0 up
sudo ip link set $VETH1 up
sudo ovs-vsctl add-port $BRIDGE_NAME $VETH0

echo "📡 Setting ONOS controller at tcp://$CONTROLLER_IP:$CONTROLLER_PORT..."
sudo ovs-vsctl set-controller $BRIDGE_NAME tcp://$CONTROLLER_IP:$CONTROLLER_PORT

echo "👀 Probing bridge to trigger OpenFlow handshake..."
sudo ovs-ofctl -O $PROTOCOL probe $BRIDGE_NAME

echo "✅ Done! Use this to verify connection on ONOS shell:"
echo "   > devices"
echo "   > ports"

#Usage
  # chmod +x setup-ovs-openflow.sh
  # ./setup-ovs-openflow.sh

