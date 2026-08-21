# DREAM Job Manager v0.1.3

One cloud-side Job Manager for `freenove-arm-01` and `ender3-printer-01`.
It does not replace or modify the existing adapters, mappers, DeviceTwins,
OctoPrint integration, or ONOS/OVS paths.

## Contracts

- Reads desired configuration from `Device.spec`.
- Reads actual state from KubeEdge v1.23 `DeviceStatus.status.twins`.
- Writes only `Device.spec.properties[name=requestedAction].desired`.
- Writes the raw compact JSON command format accepted by the working mappers.
- Requires an explicit `ALLOW` decision from DREAM Policy Management before
  writing `requestedAction`.
- Fails closed when Policy Management is unavailable or returns an invalid
  response; the job remains queued and no device command is written.
- Decodes the existing mapper `b64url:` acknowledgment format and distinguishes
  `in_progress`, `succeeded`, and `rejected` outcomes.
- Stores jobs and audit events in `/var/lib/dream/job-manager/jobs.db` on CloudNode.
- Uses one replica and Kubernetes `Recreate` strategy for SQLite safety.

Initial allowlist:

- Robot: `motor_enable`
- Printer: `status_refresh`, `print_file`, `pause`, `cancel`

No command is dispatched when a job is created. Dispatch requires a separate
API call, a fresh and eligible DeviceTwin, and an explicit policy decision.

## Build and deploy

Run from this directory on a machine with Docker credentials for `henok28`:

```bash
docker build --no-cache -t henok28/dream-job-manager:0.1.3 .
docker push henok28/dream-job-manager:0.1.3
kubectl apply -f k8s/job-manager.yaml
kubectl -n dream-maas rollout status deployment/dream-job-manager --timeout=180s
kubectl -n dream-maas get pod -o wide
```

## Verify without commanding a device

```bash
kubectl -n dream-maas port-forward service/dream-job-manager 18080:8080
```

In a second terminal:

```bash
curl -s http://127.0.0.1:18080/healthz | jq
curl -s http://127.0.0.1:18080/api/v1/devices | jq
```

## Create a safe printer validation job

Creation only queues the job:

```bash
curl -s -X POST http://127.0.0.1:18080/api/v1/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "device_id":"ender3-printer-01",
    "action":"status_refresh",
    "parameters":{},
    "idempotency_key":"printer-status-validation-001",
    "sla_class":"validation"
  }' | tee /tmp/dream-job.json | jq
```

Inspect readiness and the queued record before dispatching:

```bash
curl -s http://127.0.0.1:18080/api/v1/devices/ender3-printer-01 | jq
job_id="$(jq -r .id /tmp/dream-job.json)"
curl -s -X POST "http://127.0.0.1:18080/api/v1/jobs/$job_id/dispatch" | jq
sleep 5
curl -s "http://127.0.0.1:18080/api/v1/jobs/$job_id" | jq
```

Confirm the mapper returned the Device desired state to `NONE`:

```bash
kubectl get device ender3-printer-01 -n default -o json | jq -r \
  '.spec.properties[] | select(.name=="requestedAction") | .desired.value'
kubectl get devicestatus ender3-printer-01 -n default -o json | jq -r \
  '.status.twins[] | select(.propertyName=="requestedAction" or .propertyName=="commandAck") | [.propertyName,.reported.value] | @tsv'
```

## Safety note

The baseline policy allows only Ender-3 `status_refresh` with SLA class
`validation`. It explicitly denies printer manufacturing controls and RobotArm
physical controls until their authorization conditions are defined and tested.
