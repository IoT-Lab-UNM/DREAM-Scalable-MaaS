# DREAM Web Order App — Current Workshop Testbed

Thin Flask workshop console for the validated DREAM MaaS backend.

## Current control path

Browser → Web Order App → Job Manager → Policy Management → SLA Intelligence → KubeEdge DeviceTwin → physical device.

The Web Order App does **not** call Policy, SLA, ONOS, or Marketplace directly. Job Manager owns orchestration.

## Fixed workshop actions

- Ender-3 `status_refresh`
- Ender-3 `print_file` for pre-staged `calibration_cube_20mm.gcode`, with `confirmPhysicalStart=true`
- RobotArm `sensor_home`, with `confirmPhysicalMotion=true`
- RobotArm `move_xyz` fixed to `X0 Y200 Z45`, with `confirmPhysicalMotion=true`

No arbitrary RobotArm coordinates are accepted from the browser.

## Build on laptop

```bash
docker build -t henok28/dream-web-order-app:0.1.0 .
docker push henok28/dream-web-order-app:0.1.0
```

## Deploy from MasterNode

```bash
kubectl apply -f web-order-app-deployment.yaml
kubectl -n dream-maas rollout status deployment/web-order-app --timeout=120s
kubectl -n dream-maas get pods,svc -l app=web-order-app -o wide
```

The NodePort is `30090`. Open `http://<CloudNode-IP>:30090/` from the workshop laptop if that node/IP is reachable.
