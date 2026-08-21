# DREAM Policy Management v0.1.0

CloudNode policy-decision service for DREAM MaaS dispatch authorization. It is
separate from the Job Manager and does not access devices, mappers, OctoPrint,
or ONOS directly.

## Safety model

- Default decision is `DENY`.
- Only a fresh, eligible Ender-3 `status_refresh` job with SLA class
  `validation` is initially allowed.
- Printer manufacturing controls and RobotArm physical controls are explicitly
  denied until their authorization conditions are defined and tested.
- If this service is unavailable or returns an invalid response, Job Manager
  keeps the job queued and does not write `requestedAction`.
- Policies are versioned and mounted from the `dream-policy-rules` ConfigMap.
- Every decision has a decision ID, policy version, matched rule, reason codes,
  request ID, and timestamp.

## API

- `GET /healthz`
- `GET /api/v1/policies`
- `POST /api/v1/policy/evaluate`

## Build

```bash
docker build --no-cache -t henok28/dream-policy-management:0.1.0 .
docker push henok28/dream-policy-management:0.1.0
```

Deploy Policy Management before Job Manager v0.1.3:

```bash
kubectl apply -f policy_manager_deployment.yaml
kubectl -n dream-maas rollout status \
  deployment/dream-policy-management --timeout=180s
```

## ONOS boundary

The earlier prototype forwarded policy objects to an example ONOS endpoint and
stored them only in process memory. That unverified write path is intentionally
not enabled here. The validated ONOS/OVS/VXLAN configuration remains untouched;
policy-to-ONOS coordination will be added later through a separately tested
adapter and enforcement contract.
