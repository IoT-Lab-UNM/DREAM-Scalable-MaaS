import base64
import json
from datetime import datetime, timezone


DEVICE_PROFILES = {
    "freenove-arm-01": {
        "kind": "robot",
        "freshness_seconds": 15,
        "actions": {"motor_enable"},
    },
    "ender3-printer-01": {
        "kind": "printer",
        "freshness_seconds": 30,
        "actions": {"status_refresh", "print_file", "pause", "cancel"},
    },
}


def utcnow():
    return datetime.now(timezone.utc)


def iso_now():
    return utcnow().isoformat().replace("+00:00", "Z")


def encode_command(command_id, job_id, action, parameters):
    payload = {
        "command_id": command_id,
        "job_id": job_id,
        "action": action,
        "parameters": parameters,
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=False).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("="), payload


def twins_to_map(device_status):
    twins = device_status.get("status", {}).get("twins", [])
    result = {}
    for twin in twins:
        name = twin.get("propertyName")
        if name:
            result[name] = twin.get("reported", {}).get("value")
    return result


def parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def readiness(device_id, device_status, now=None):
    now = now or utcnow()
    profile = DEVICE_PROFILES[device_id]
    twins = twins_to_map(device_status)
    reasons = []

    if str(device_status.get("status", {}).get("state", "")).lower() != "online":
        reasons.append("device_status_not_online")
    if twins.get("availability") != "ONLINE":
        reasons.append("availability_not_online")
    if twins.get("fault") not in (None, "", "NONE"):
        reasons.append("fault_present")

    updated = parse_time(twins.get("lastUpdate"))
    age = None
    if updated is None:
        reasons.append("last_update_missing_or_invalid")
    else:
        age = max(0.0, (now - updated).total_seconds())
        if age > profile["freshness_seconds"]:
            reasons.append("twin_stale")

    if profile["kind"] == "robot":
        if twins.get("operatingState") != "READY":
            reasons.append("robot_not_ready")
        if twins.get("currentTask") not in (None, "", "NONE"):
            reasons.append("robot_busy")
    else:
        if twins.get("printerState") != "Operational":
            reasons.append("printer_not_operational")
        if twins.get("activeJob") not in (None, "", "NONE"):
            reasons.append("printer_busy")

    return {
        "eligible": not reasons,
        "reasons": reasons,
        "freshness_age_seconds": None if age is None else round(age, 3),
        "freshness_limit_seconds": profile["freshness_seconds"],
        "twins": twins,
    }


def ack_matches(command_id, value):
    if not value or value == "NONE":
        return False
    if command_id in value:
        return True
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    return parsed.get("command_id") == command_id
