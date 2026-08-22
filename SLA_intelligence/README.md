# DREAM SLA Intelligence v0.1.0

Minimal CloudNode SLA admission and telemetry service for the DREAM MaaS
baseline. It is deterministic and auditable; it does not claim to provide an
ML predictor.

## Responsibilities

- Accept latest edge/network telemetry through `POST /api/v1/telemetry`.
- Evaluate `validation`, `standard`, and `priority` SLA classes.
- Return `ADMIT` or `REJECT`, score, risk, reason codes, observations,
  thresholds, version, decision ID, and timestamp.
- Expose restart-local operational counters at `GET /api/v1/kpis`.
- Log every SLA decision as structured JSON.

The Job Manager remains the durable audit owner: it saves each SLA result in
the existing SQLite job-event history. This service intentionally has no
database in the baseline.

## Safety contract

The service does not access Kubernetes, KubeEdge, devices, ONOS, OVS, or
OctoPrint. The Job Manager calls it after readiness and Policy Management have
both succeeded and before `requestedAction` is written. An SLA rejection,
outage, timeout, or malformed response blocks dispatch.

## API

- `GET /healthz`
- `GET /readyz`
- `GET /api/v1/sla/classes`
- `POST /api/v1/telemetry`
- `GET /api/v1/telemetry/<device_id>`
- `POST /api/v1/sla/evaluate`
- `GET /api/v1/kpis`

The `validation` class keeps network telemetry optional until the two edge
Telemetry Agents are deployed. `priority` already requires current network
telemetry, which provides an explicit integration target for that phase.

## Build

```bash
docker build --no-cache \
  -t henok28/dream-sla-intelligence:0.1.0 .

docker push henok28/dream-sla-intelligence:0.1.0
```

## Deploy

```bash
kubectl apply -f k8s/sla-intelligence.yaml

kubectl -n dream-maas rollout status \
  deployment/dream-sla-intelligence \
  --timeout=180s
```
