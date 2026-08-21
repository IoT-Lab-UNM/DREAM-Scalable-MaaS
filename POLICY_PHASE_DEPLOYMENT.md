# DREAM Policy Management deployment checkpoint

This checkpoint adds a separate Policy Management microservice on CloudNode and
integrates it with the single Job Manager. It does not modify device adapters,
mappers, DeviceTwins, OctoPrint, or ONOS/OVS paths.

## Images

- `henok28/dream-policy-management:0.1.0`
- `henok28/dream-job-manager:0.1.3`

Build both images from their respective directories on the authorized build
machine, push them to Docker Hub, and deploy Policy Management before Job
Manager.

## Baseline decision behavior

| Request | Decision |
| --- | --- |
| Ender-3 `status_refresh`, SLA `validation`, eligible twin | `ALLOW` |
| Ender-3 physical action | `DENY` |
| RobotArm `motor_enable` | `DENY` |
| No matching rule | `DENY` |
| Policy service unavailable or malformed response | Dispatch blocked; job remains `QUEUED` |

## Deployment order

```bash
kubectl apply -f \
  policy-management-system/policy_manager_deployment.yaml
kubectl -n dream-maas rollout status \
  deployment/dream-policy-management --timeout=180s

kubectl apply -f job_manager/k8s/job-manager.yaml
kubectl -n dream-maas rollout status \
  deployment/dream-job-manager --timeout=180s
```

## Service checks

```bash
kubectl -n dream-maas get pods -o wide
kubectl -n dream-maas get services
kubectl -n dream-maas port-forward \
  service/dream-policy-management 18090:8090
```

```bash
curl -s http://127.0.0.1:18090/healthz | jq
curl -s http://127.0.0.1:18090/api/v1/policies | jq
```

Perform allow, deny, and service-unavailable tests only after both deployments
are healthy. Use new idempotency keys for every test and verify that denied or
unavailable requests never change Device `requestedAction` from `NONE`.
