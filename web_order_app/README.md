# Web Order App for Scalable DIAM MaaS

This folder contains a deployable Web Order App for the cloud-side MaaS architecture.

The app is designed to run on `cloudnode` and act as the entry point for manufacturing requests.

```text
Remote MaaS Client
→ Web Order App
→ Job Manager / Marketplace / Policy Management / SLA Intelligence
→ selected manufacturing edge gateway
→ 3D printer or robot arm
→ telemetry feedback
```

## Features

- Web UI for submitting manufacturing orders
- Multi-site demo selection logic across NMSU / NMT / NTU
- Device selection for 3D printer or robot arm
- Routing modes: AUTO or SITE
- SLA tiers: standard, urgent, cost optimized
- REST API endpoints
- Prometheus `/metrics`
- Kubernetes deployment pinned to `cloudnode`
- NodePort service on port `30080`

## Deployment

On the CloudNode, run:

```bash
cd web-order-app
chmod +x setup_webOrderApp.sh
./setup_webOrderApp.sh
```

Then check:

```bash
kubectl get pods -n maas -o wide
kubectl get svc web-order-app -n maas
```

Open:

```text
http://<cloudnode-ip>:30080
```

## API Examples

Health:

```bash
curl http://<cloudnode-ip>:30080/api/health
```

Submit an order:

```bash
curl -X POST http://<cloudnode-ip>:30080/api/orders \
  -H "Content-Type: application/json" \
  -d '{
    "client_location": "California / West Coast",
    "routing_mode": "SITE",
    "preferred_site": "NTU",
    "device_type": "3d_printer",
    "sla_tier": "standard",
    "material": "PLA",
    "deadline_minutes": 120
  }'
```

List orders:

```bash
curl http://<cloudnode-ip>:30080/api/orders
```

## Notes

The app currently runs in `DEMO_MODE=true`, so it performs local selection logic without requiring the other microservices to already exist.

Later, set `DEMO_MODE=false` and update the ConfigMap URLs to connect to real services:

- Job Manager
- Marketplace
- Policy Management System
- SLA Intelligence
- ONOS SDN Controller

## Selection Inputs

The demo selection logic uses:

```text
health
queue length
RTT
availability
client location
routing mode
preferred site
SLA tier
```
