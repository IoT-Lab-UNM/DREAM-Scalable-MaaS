Step 1: opening state:

echo
echo "--- MaaS services ---"
kubectl -n dream-maas get pods -o wide

echo
echo "--- Monitoring ---"
kubectl -n monitoring get pods -o wide

echo
echo "--- Printer ---"
curl -sS http://127.0.0.1:18080/api/v1/devices/ender3-printer-01 | \
jq '{
  state,
  eligible:.readiness.eligible,
  printerState:.readiness.twins.printerState,
  activeJob:.readiness.twins.activeJob,
  requestedAction:.readiness.twins.requestedAction
}'

echo
echo "--- Robot ---"
curl -sS http://127.0.0.1:18080/api/v1/devices/freenove-arm-01 | \
jq '{
  state,
  eligible:.readiness.eligible,
  operatingState:.readiness.twins.operatingState,
  currentTask:.readiness.twins.currentTask,
  requestedAction:.readiness.twins.requestedAction
}'

Step 2: Web order app and grafana

Web Order App:
http://10.12.10.124:30090

Grafana:
http://10.12.10.124:30092

"This demonstration shows our scalable Manufacturing-as-a-Service framework across the cloud-edge continuum. A manufacturing request enters through the Web Order App and is handled by a centralized Job Manager. Before reaching the physical equipment, it passes policy authorization and SLA admission. The accepted command is then synchronized through KubeEdge DeviceTwin to the appropriate edge node, where a device-specific mapper and adapter translate the generic MaaS action into the physical device protocol. Today we are demonstrating this with two heterogeneous devices a Creality Ender-3 3D printer and a Freenove robotic arm. At the same time, telemetry, SDN connectivity, and security status are monitored live through Prometheus and Grafana:"

"The backend knows which device-specific action is required, while the policy and SLA services determine whether that action is currently permitted:"

"Here we can see both edge devices reporting live telemetry, both SDN paths connected to ONOS, current network RTT and jitter, queue depth, security enforcement state, and MaaS requests generated through the Web Order App:"

Step 2 — prepare the RobotArm:
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

confirm there are no outstanding robot jobs:

echo "===== ACTIVE ROBOT JOBS ====="

curl -sS http://127.0.0.1:18080/api/v1/jobs | \
jq '
  map(
    select(
      .device_id=="freenove-arm-01" and
      (.state=="QUEUED" or .state=="DISPATCHED" or .state=="ACKNOWLEDGED")
    )
  )
  | map({id,action,state,created_at,last_error})
'

verify the robot is ready:

curl -sS \
  http://127.0.0.1:18080/api/v1/devices/freenove-arm-01 | \
jq '{
  state,
  eligible:.readiness.eligible,
  freshness:.readiness.freshness_age_seconds,
  operatingState:.readiness.twins.operatingState,
  currentTask:.readiness.twins.currentTask,
  requestedAction:.readiness.twins.requestedAction,
  fault:.readiness.twins.fault
}'

Mosquitto acknowledgement monitor on the Arm:

mosquitto_sub \
  -h 127.0.0.1 \
  -p 1883 \
  -t 'dream/v1/sites/unm-lab/devices/freenove-arm-01/acks' \
  -v

Check if the motors are relaxed or not:.....

On the Job order app web interface:
Sensor home.......The user does not send a vendor-specific robot command. The Web Order App creates a generic sensor_home job and sends it to the Job Manager. 
Before dispatch, Policy Management verifies that physical motion is explicitly authorized, including the confirmPhysicalMotion requirement. SLA Intelligence then evaluates current device and network conditions.
After admission, the action is synchronized through KubeEdge DeviceTwin to the edge mapper. The Robot Adapter validates it and translates sensor_home into the Freenove protocol command S10 F1.



