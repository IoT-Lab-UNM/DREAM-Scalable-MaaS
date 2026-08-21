import base64
import binascii
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

    raw_json = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=False,
    )

    return raw_json, payload


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


def parse_ack(value):
    """Decode a mapper acknowledgment without changing mapper behavior."""
    if value in (None, "", "NONE"):
        return None

    if isinstance(value, dict):
        parsed = value.copy()
    else:
        text = str(value).strip()
        try:
            if text.startswith("b64url:"):
                encoded = text.removeprefix("b64url:")
                encoded += "=" * (-len(encoded) % 4)
                decoded = base64.urlsafe_b64decode(encoded).decode("utf-8")
                parsed = json.loads(decoded)
            else:
                parsed = json.loads(text)
        except (
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            binascii.Error,
        ):
            return None

    if not isinstance(parsed, dict):
        return None

    command_id = str(parsed.get("command_id", "")).strip()
    status = str(parsed.get("status", "")).strip().lower()
    if not command_id:
        return None

    parsed["command_id"] = command_id
    parsed["status"] = status
    return parsed


def ack_matches(command_id, value):
    parsed = parse_ack(value)
    return parsed is not None and parsed["command_id"] == command_id
