# Architecture

## Infrastructure

### Laptop 1 — Hub / Cloud
- Ubuntu 24.04.4 LTS
- Connected behind an **Xfinity router**
- Local IP on Wi-Fi/LAN: typically `10.0.0.7`
- Public IPv4 obtained from `curl -4 ifconfig.me`
- Runs:
  - WireGuard
  - Mosquitto (MQTT)
  - MinIO

### Laptop 2 — Edge
- Ubuntu 24.04.4 LTS
- Connected to a different network / ISP (**Ultra Mobile** in the working case)
- Runs:
  - WireGuard
  - mosquitto-clients
  - Python virtual environment
  - edge processing agent (`print_agent.py`)

## Logical topology

```text
Laptop 2 (Edge)  <--WireGuard over Internet-->  Laptop 1 (Hub)
10.250.1.1/32                                   10.250.0.1/16
```

## Overlay behavior

- The Edge only routes to the Hub overlay IP.
- No local LAN subnet is advertised through the tunnel.
- The Hub exposes MinIO and MQTT over the overlay.

## Application flow

```text
1. Operator uploads file to MinIO bucket `prints`
2. Operator publishes MQTT job to topic `print/jobs`
3. Edge agent receives the message
4. Edge agent downloads the object over the VPN
5. Edge agent performs local processing
```

## Networking prerequisites

Because Laptop 1 is behind NAT/router:

- The Hub laptop must listen on UDP `51820`
- Ubuntu firewall must allow `51820/udp`
- The **router must port-forward UDP 51820 → Hub LAN IP:51820**

Example:

```text
UDP 51820 -> 10.0.0.7:51820
```

## Key lesson from debugging

The tunnel did **not** handshake when both laptops were effectively on the same public NAT path. It worked correctly when Laptop 2 moved to a **different wireless network / ISP**.

