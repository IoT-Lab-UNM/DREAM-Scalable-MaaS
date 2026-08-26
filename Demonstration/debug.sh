Enable RobotArm motors:

Mosquitto subscriber:
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
mosquitto_sub \
  -h 127.0.0.1 \
  -p 1883 \
  -t 'dream/v1/sites/unm-lab/devices/freenove-arm-01/acks' \
  -v
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
ROBOT_CMD_ID="manual-motor-enable-$(date +%s)"

ROBOT_REQUESTED_ACTION="$(
  ROBOT_CMD_ID="$ROBOT_CMD_ID" python3 - <<'PY'
import base64
import json
import os

command = {
    "command_id": os.environ["ROBOT_CMD_ID"],
    "job_id": "manual-robot-control",
    "action": "motor_enable",
    "parameters": {}
}

raw = json.dumps(command, separators=(",", ":")).encode()
print("b64url:" + base64.urlsafe_b64encode(raw).decode().rstrip("="))
PY
)"

REQ_INDEX="$(
  kubectl get device freenove-arm-01 -n default -o json |
  jq -r '.spec.properties | to_entries[] |
         select(.value.name=="requestedAction") | .key'
)"

kubectl patch device freenove-arm-01 -n default \
  --type='json' \
  -p="[
    {
      \"op\":\"replace\",
      \"path\":\"/spec/properties/$REQ_INDEX/desired/value\",
      \"value\":\"$ROBOT_REQUESTED_ACTION\"
    }
  ]"

sleep 3

kubectl patch device freenove-arm-01 -n default \
  --type='json' \
  -p="[
    {
      \"op\":\"replace\",
      \"path\":\"/spec/properties/$REQ_INDEX/desired/value\",
      \"value\":\"NONE\"
    }
  ]"

echo "RobotArm motor_enable command sent."
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

Relax RobotArm motors:

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

ROBOT_CMD_ID="manual-motor-relax-$(date +%s)"

ROBOT_REQUESTED_ACTION="$(
  ROBOT_CMD_ID="$ROBOT_CMD_ID" python3 - <<'PY'
import base64
import json
import os

command = {
    "command_id": os.environ["ROBOT_CMD_ID"],
    "job_id": "manual-robot-control",
    "action": "motor_relax",
    "parameters": {}
}

raw = json.dumps(command, separators=(",", ":")).encode()
print("b64url:" + base64.urlsafe_b64encode(raw).decode().rstrip("="))
PY
)"

REQ_INDEX="$(
  kubectl get device freenove-arm-01 -n default -o json |
  jq -r '.spec.properties | to_entries[] |
         select(.value.name=="requestedAction") | .key'
)"

kubectl patch device freenove-arm-01 -n default \
  --type='json' \
  -p="[
    {
      \"op\":\"replace\",
      \"path\":\"/spec/properties/$REQ_INDEX/desired/value\",
      \"value\":\"$ROBOT_REQUESTED_ACTION\"
    }
  ]"

sleep 3

kubectl patch device freenove-arm-01 -n default \
  --type='json' \
  -p="[
    {
      \"op\":\"replace\",
      \"path\":\"/spec/properties/$REQ_INDEX/desired/value\",
      \"value\":\"NONE\"
    }
  ]"

echo "RobotArm motor_relax command sent."
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%