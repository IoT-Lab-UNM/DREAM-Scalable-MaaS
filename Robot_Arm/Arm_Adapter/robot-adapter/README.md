# DREAM RobotArm Adapter 0.1.0

Headless MQTT-to-Freenove TCP adapter for the `robotarm` KubeEdge node.

## Confirmed interfaces

- Freenove server: TCP `status.hostIP:5000`, CRLF-delimited UTF-8 commands.
- Existing edge Mosquitto: `127.0.0.1:1883` through `hostNetwork: true`.
- Server accepts only one client. Disconnect the PyQt GUI before starting this pod.

## MQTT topics

- Commands: `dream/v1/sites/unm-lab/devices/freenove-arm-01/commands`
- Acknowledgments: `.../acks`
- Retained state: `.../state`

Example safe command:

```json
{"command_id":"test-001","job_id":"manual-test","action":"motor_enable","parameters":{}}
```

Example coordinate move (use only after motor enable and sensor-home validation):

```json
{"command_id":"test-002","job_id":"manual-test","action":"move_xyz","parameters":{"x":0,"y":200,"z":45}}
```

## Safety and semantics

- Default bounds: X `[-100,100]`, Y `[150,250]`, Z `[0,120]`; adjust only after hardware validation.
- `S13` is disabled because it terminates the Freenove server.
- The current server reports queue depth only. `sent` and `queue_count=0` do **not** prove physical completion.
- SQLite command IDs prevent duplicate MQTT deliveries from repeating a physical action.
- The adapter deliberately does not import PyQt, OpenCV, GUI assets, forced thread termination, or client calibration writes.

## Build and deploy

Prepare the persistent command-ID database directory once on `robotarm`:

```bash
sudo install -d -o 10001 -g 10001 /var/lib/dream/robot-adapter
```

Build a multi-architecture image in your normal registry workflow, replace the image field in the manifest, then:

```bash
kubectl apply -f kubernetes/robot-adapter.yaml
kubectl get pods -n kubeedge -o wide
kubectl logs -n kubeedge deploy/robot-adapter -f
```

Start testing with `motor_enable`, then `sensor_home`, then the known home coordinate. Keep one person near the hardware and be ready to cut motor power.
