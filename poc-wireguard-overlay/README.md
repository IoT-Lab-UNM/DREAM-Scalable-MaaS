# DREAM Project — Reproducible 2-Laptop Overlay VPN POC

This package documents a professional, reproducible proof of concept (POC) for a **2-laptop Ubuntu deployment** of an **overlay-only site-to-cloud VPN architecture** using:

- **WireGuard** for the overlay VPN
- **Mosquitto (MQTT)** for event messaging
- **MinIO** for object storage
- **Python edge agent** for local processing after a remote trigger

It was developed from a real deployment and debugging session using:

- **Laptop 1 (Hub):** Ubuntu 24.04.4 LTS, behind an **Xfinity** home router/NAT
- **Laptop 2 (Edge):** Ubuntu 24.04.4 LTS, connected through **Ultra Mobile** / another Internet provider

The POC demonstrates:

1. secure **site-to-cloud VPN** connectivity,
2. an **overlay-only** communication model,
3. **centralized cloud services** on the Hub,
4. **event-driven file distribution** with MQTT,
5. **object retrieval from MinIO**, and
6. **local Edge processing** after remote trigger.

---

## Package structure

```text
DREAM-Project-poc/
├── README.md
├── docs/
│   ├── architecture.md
│   ├── step-by-step.md
│   ├── troubleshooting.md
│   └── push-to-github.md
├── configs/
│   ├── hub/
│   │   └── wg0.conf.example
│   └── edge/
│       └── wg0.conf.example
├── docker/
│   ├── docker-compose.yml
│   └── mosquitto.conf
├── scripts/
│   ├── hub/
│   │   ├── show_hub_public_ip.sh
│   │   └── install_minio_mc.sh
│   └── edge/
│       ├── update_edge_endpoint.sh
│       └── start_print_agent.sh
└── edge/
    └── print_agent.py
```

---

## Important security note

During the live debugging process, real private keys were temporarily used to validate connectivity. **Do not commit real private keys to GitHub.**

Before publishing:

- regenerate WireGuard keys,
- keep only placeholder-based templates in Git,
- remove any real secrets from shell history and files.

---

## Quick start

Read these in order:

1. `docs/architecture.md`
2. `docs/step-by-step.md`
3. `docs/troubleshooting.md`
4. `docs/push-to-github.md`

