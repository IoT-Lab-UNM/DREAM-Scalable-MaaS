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

Step 3: Demonstrate the print job:

The same MaaS control plane is now managing a completely different physical device. The request is still expressed as a generic manufacturing action, but the edge mapper translates it into the printer-specific OctoPrint workflow.

Step 3: Security/SDN enforcement
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

NORMAL
Web App → Job Manager → Policy → SLA → RobotArm works

ISOLATE
Security Agent → ONOS/OVS drop flows
→ robot path unavailable / stale
→ Job Manager readiness fails
→ MaaS action blocked

RESTORE
Security Agent removes isolation flows
→ telemetry/twin becomes fresh
→ eligible=true
→ MaaS action works again

verify the robot is clean:
%%%%%%%%%%%%%%%%%%%
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

check there is no active robot queue:
%%%%%%%%%%%%%%%%%%%%%%%%
curl -sS http://127.0.0.1:18080/api/v1/jobs | \
jq '
  map(
    select(
      .device_id=="freenove-arm-01" and
      (.state=="QUEUED" or .state=="DISPATCHED" or .state=="ACKNOWLEDGED")
    )
  )
'

Show ONOS / OVS normal state:
%%%%%%%%%%%%%%%%%%%%%%%%%

on arm:
%%%%%%%%%%
echo "===== ROBOT OVS BEFORE ISOLATION ====="

sudo ovs-ofctl -O OpenFlow13 dump-flows br-dream | \
  grep -E 'priority=49001|priority=49002|actions=drop' || \
  echo "No active DREAM isolation drop flows"

On the MasterNode, first retrieve the current secret:
%%%%%%%%%%
SEC_TOKEN="$(
  kubectl -n edge-agents get secret dream-security-agent-auth \
  -o jsonpath='{.data.token}' | base64 -d
)"

echo "token_loaded=${#SEC_TOKEN}"

isolate the RobotArm:
%%%%%%%%%%%
curl -sS -X POST \
  http://10.12.11.228:9102/api/v1/enforce \
  -H "Authorization: Bearer $SEC_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "device_id": "freenove-arm-01",
    "action": "enforce"
  }' | jq

Show the actual SDN effect:
%%%%%%%%%%%%
echo "===== ROBOT OVS AFTER ISOLATION ====="

sudo ovs-ofctl -O OpenFlow13 dump-flows br-dream | \
  grep -E 'priority=49001|priority=49002'

through Prometheus on the MasterNode: Expected value 1
%%%%%%%%%%%%%%%%%%%%%%%%%%
curl -sG \
  http://10.12.10.124:30091/api/v1/query \
  --data-urlencode \
  'query=dream_security_enforcement_active{device_id="freenove-arm-01"}' | jq

Also the grafana interface
%%%%%%%%%%%%%

Query the prometheus url: Expect 1
%%%%%%%%%%
curl -sG \
  http://10.12.10.124:30091/api/v1/query \
  --data-urlencode \
  'query=dream_security_enforcement_active{device_id="freenove-arm-01"}' | \
  jq -r '.data.result[].value[1]'

Restore the isolation on the master node:
%%%%%%%%%%%%%%%%%%

curl -sS -X POST \
  http://10.12.11.228:9102/api/v1/enforce \
  -H "Authorization: Bearer $SEC_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "device_id": "freenove-arm-01",
    "action": "release"
  }' | jq

Query prometheus again to check: Expect 0
%%%%%%%%%%%%%

curl -sG \
  http://10.12.10.124:30091/api/v1/query \
  --data-urlencode \
  'query=dream_security_enforcement_active{device_id="freenove-arm-01"}' | \
  jq -r '.data.result[].value[1]'


Enter into ONOS: to see the two switches deployed in the edges using SBI OF1.3
Here we are inside the ONOS control plane itself. ONOS sees two physical OpenFlow switches, one associated with the 
RobotArm and one with the Ender-3. When the DREAM Security Agent receives an authenticated enforcement request, it programs 
high-priority isolation rules through the SDN control plane. We can see those rules appear directly in ONOS and in the edge OVS flow table. 
When enforcement is released, the rules are removed again. Grafana independently captures the same enforcement transition and SDN state.
%%%%%%%%%%%%%%%%%%%%%%%%%%%
RobotArm   of:0000000000000011
Ender-3    of:0000000000000012
%%%%%%%%%%%%%%%%%%%%%%%%%

Identify the pod:
%%%%%%%%%%%%%
kubectl -n sdn get pods -o wide

Enter into ONOS:
%%%%%%%%%%%%%%%%%%%
ONOS_POD=$(kubectl -n sdn get pods -l app=onos-controller -o jsonpath='{.items[0].metadata.name}')
echo "$ONOS_POD"

kubectl -n sdn exec -it "$ONOS_POD" -- /bin/bash

Enter the Karaf CLI — inside the ONOS container:
cd /root/onos/apache-karaf-4.2.14/bin
./client

Start with the devices:
devices

Remark: These are the two physical edge OpenFlow switches. ONOS sees the RobotArm gateway and the Ender-3 gateway as independent programmable network elements.

Inspect the ports:
ports

Remark: ONOS is not just aware of the switch; it has visibility into the individual ingress and egress interfaces used by the manufacturing data path.

Show all ONOS flows:
flows

compare flows before and after Security Agent enforcement:
MasterNode: Trigger RobotArm isolation:
%%%%%%%%%%%%%%%%
SEC_TOKEN="$(
  kubectl -n edge-agents get secret dream-security-agent-auth \
  -o jsonpath='{.data.token}' | base64 -d
)"

curl -sS -X POST \
  http://10.12.11.228:9102/api/v1/enforce \
  -H "Authorization: Bearer $SEC_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "device_id": "freenove-arm-01",
    "action": "enforce"
  }' | jq

And check flows in ONOS cli:
flows

Show controller roles
roles




