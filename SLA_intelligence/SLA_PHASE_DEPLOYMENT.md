# DREAM SLA Intelligence deployment checkpoint

This checkpoint adds one SLA Intelligence microservice on CloudNode and updates
the existing CloudNode Job Manager from v0.1.3 to v0.1.4. It does not modify the
RobotArm or Ender-3 adapters, mappers, DeviceTwins, OctoPrint, Policy Management,
ONOS, OVS, VXLAN, or established SDN rules.

## Decision order

```text
Device readiness -> Policy ALLOW -> SLA ADMIT -> requestedAction dispatch
```

Any failure before the last step results in no DeviceTwin command write.

## Source validation on the laptop

Run from the repository root after replacing `job_manager` and adding
`SLA_intelligence`:

```bash
python3 -m venv /tmp/dream-sla-validation
source /tmp/dream-sla-validation/bin/activate

python -m pip install \
  -r job_manager/requirements.txt \
  -r SLA_intelligence/requirements.txt

PYTHONPATH=job_manager \
python -m unittest discover -s job_manager/tests -v

PYTHONPATH=SLA_intelligence \
python -m unittest discover -s SLA_intelligence/tests -v

deactivate
git diff --check
git status
```

Expected baseline: 19 Job Manager tests and 7 SLA Intelligence tests pass.

## Build and push on the laptop

```bash
docker build --no-cache \
  -t henok28/dream-sla-intelligence:0.1.0 \
  SLA_intelligence

docker run --rm \
  henok28/dream-sla-intelligence:0.1.0 \
  python -m py_compile /app/app.py /app/engine.py

docker build --no-cache \
  -t henok28/dream-job-manager:0.1.4 \
  job_manager

docker run --rm \
  henok28/dream-job-manager:0.1.4 \
  python -m py_compile \
  /app/app.py /app/core.py /app/store.py \
  /app/kubeedge_client.py /app/policy_client.py /app/sla_client.py

docker push henok28/dream-sla-intelligence:0.1.0
docker push henok28/dream-job-manager:0.1.4
```

Commit and push the source only after these commands succeed.

## Deploy from the masternode

Deploy SLA Intelligence first, then update Job Manager:

```bash
cd ~/DREAM-Scalable-MaaS
git pull --ff-only

kubectl apply -f SLA_intelligence/k8s/sla-intelligence.yaml
kubectl -n dream-maas rollout status \
  deployment/dream-sla-intelligence --timeout=180s

kubectl apply -f job_manager/k8s/job-manager.yaml
kubectl -n dream-maas rollout status \
  deployment/dream-job-manager --timeout=180s

kubectl -n dream-maas get pods -o wide
```

Verify both service paths from inside Job Manager:

```bash
kubectl -n dream-maas exec deployment/dream-job-manager -- \
  python -c 'import urllib.request; print(urllib.request.urlopen("http://dream-policy-management:8090/healthz", timeout=3).read().decode()); print(urllib.request.urlopen("http://dream-sla-intelligence:8070/healthz", timeout=3).read().decode())'
```

Keep the existing Job Manager port-forward. In a second masternode terminal,
also start the SLA port-forward:

```bash
kubectl -n dream-maas port-forward \
  service/dream-sla-intelligence 18070:8070
```

## Live exit tests

### 1. ADMIT and complete

First make sure the printer readiness is eligible, then create a new Ender-3
`status_refresh` job with SLA class `validation`. Dispatch it through the
existing Job Manager port-forward. The final event order must include:

```text
JOB_QUEUED
POLICY_ALLOWED
SLA_ADMITTED
COMMAND_DISPATCHED
COMMAND_ACKNOWLEDGED
JOB_COMPLETED
```

The final job must show `policy_decision=ALLOW`, `sla_decision=ADMIT`, and
`state=COMPLETED`. Printer `requestedAction` must return to `NONE`.

### 2. Deterministic SLA rejection with no device command

Record the current desired command and acknowledgment, then inject a fresh but
out-of-SLA RTT sample:

```bash
curl -s -X POST http://127.0.0.1:18070/api/v1/telemetry \
  -H 'Content-Type: application/json' \
  -d "{\"device_id\":\"ender3-printer-01\",\"site_id\":\"unm-lab\",\"observed_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"metrics\":{\"rtt_ms\":900,\"loss_percent\":0,\"jitter_ms\":2,\"queue_depth\":0}}" | jq
```

Create and dispatch another safe `status_refresh`/`validation` job. Policy must
allow it, SLA must return HTTP 409 with `decision=REJECT`, and the job must be
`FAILED` with `SLA_REJECTED`. There must be no `COMMAND_DISPATCHED` event. The
Device desired command and mapper acknowledgment must be unchanged.

Restore healthy telemetry:

```bash
curl -s -X POST http://127.0.0.1:18070/api/v1/telemetry \
  -H 'Content-Type: application/json' \
  -d "{\"device_id\":\"ender3-printer-01\",\"site_id\":\"unm-lab\",\"observed_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"metrics\":{\"rtt_ms\":20,\"loss_percent\":0,\"jitter_ms\":2,\"queue_depth\":0}}" | jq
```

Create a new validation job and confirm it completes.

### 3. Fail closed and recover

Create but do not dispatch a fresh validation job. Scale SLA Intelligence to
zero, dispatch the queued job, and expect HTTP 503, `sla_decision=ERROR`, state
`QUEUED`, and event `SLA_UNAVAILABLE`. Verify no command was written.

```bash
kubectl -n dream-maas scale deployment/dream-sla-intelligence --replicas=0
kubectl -n dream-maas wait --for=delete pod \
  -l app=dream-sla-intelligence --timeout=60s
```

Restore the service and retry the same queued job:

```bash
kubectl -n dream-maas scale deployment/dream-sla-intelligence --replicas=1
kubectl -n dream-maas rollout status \
  deployment/dream-sla-intelligence --timeout=180s
```

The same job must then show `SLA_ADMITTED`, dispatch, acknowledge, and complete.

## Evidence checkpoint

```bash
evidence_dir="$HOME/dream-baseline/evidence/sla-intelligence-v0.1.0"
mkdir -p "$evidence_dir"

kubectl -n dream-maas get deployment dream-sla-intelligence -o yaml \
  > "$evidence_dir/sla-deployment.yaml"
kubectl -n dream-maas get deployment dream-job-manager -o yaml \
  > "$evidence_dir/job-manager-deployment.yaml"
kubectl -n dream-maas get configmap dream-sla-classes -o yaml \
  > "$evidence_dir/sla-classes.yaml"
kubectl -n dream-maas get pods -o wide > "$evidence_dir/pods.txt"
kubectl -n dream-maas logs deployment/dream-sla-intelligence --since=1h \
  > "$evidence_dir/sla.log"
kubectl -n dream-maas logs deployment/dream-job-manager --since=1h \
  > "$evidence_dir/job-manager.log"
curl -s http://127.0.0.1:18070/api/v1/kpis \
  > "$evidence_dir/kpis.json"

sha256sum "$evidence_dir"/* > "$evidence_dir/SHA256SUMS"
```

Copy the final ADMIT, REJECT, fail-closed, and recovery job JSON files into the
same evidence directory before generating `SHA256SUMS`.
