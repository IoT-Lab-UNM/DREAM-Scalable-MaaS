import os
import threading
import time

from flask import Flask, jsonify, request

from core import (
    DEVICE_PROFILES,
    encode_command,
    iso_now,
    parse_ack,
    parse_time,
    readiness,
    twins_to_map,
    utcnow,
)
from kubeedge_client import KubeEdgeClient
from policy_client import PolicyClient, PolicyProtocolError, PolicyUnavailable
from store import JobStore


DB_PATH = os.getenv("JOB_DB_PATH", "/data/jobs.db")
DEVICE_NAMESPACE = os.getenv("DEVICE_NAMESPACE", "default")
ACK_TIMEOUT_SECONDS = int(os.getenv("ACK_TIMEOUT_SECONDS", "60"))
POLICY_URL = os.getenv(
    "POLICY_URL",
    "http://dream-policy-management:8090",
)
POLICY_TIMEOUT_SECONDS = float(os.getenv("POLICY_TIMEOUT_SECONDS", "3"))

app = Flask(__name__)
store = JobStore(DB_PATH)
kube = KubeEdgeClient()
policy = PolicyClient(POLICY_URL, POLICY_TIMEOUT_SECONDS)


def error(message, status=400, **extra):
    return jsonify({"error": message, **extra}), status


def project_status(obj):
    name = obj.get("metadata", {}).get("name")
    result = readiness(name, obj) if name in DEVICE_PROFILES else None
    return {
        "device_id": name,
        "state": obj.get("status", {}).get("state"),
        "last_online_time": obj.get("status", {}).get("lastOnlineTime"),
        "readiness": result,
    }


@app.get("/healthz")
def health():
    return jsonify({"status": "ok", "service": "dream-job-manager"})


@app.get("/api/v1/devices")
def devices():
    objects = kube.list_statuses(DEVICE_NAMESPACE)
    return jsonify([project_status(obj) for obj in objects if obj.get("metadata", {}).get("name") in DEVICE_PROFILES])


@app.get("/api/v1/devices/<device_id>")
def device(device_id):
    if device_id not in DEVICE_PROFILES:
        return error("unknown device", 404)
    return jsonify(project_status(kube.device_status(DEVICE_NAMESPACE, device_id)))


@app.post("/api/v1/jobs")
def create_job():
    body = request.get_json(silent=True) or {}
    device_id = body.get("device_id")
    action = body.get("action")
    parameters = body.get("parameters", {})
    if device_id not in DEVICE_PROFILES:
        return error("unknown device_id")
    if action not in DEVICE_PROFILES[device_id]["actions"]:
        return error(
            "action is not allowed for this device",
            allowed_actions=sorted(DEVICE_PROFILES[device_id]["actions"]),
        )
    if not isinstance(parameters, dict):
        return error("parameters must be a JSON object")
    if action == "print_file" and not parameters.get("artifact_id"):
        return error("print_file requires parameters.artifact_id")
    item, created = store.create(
        device_id=device_id,
        device_kind=DEVICE_PROFILES[device_id]["kind"],
        action=action,
        parameters=parameters,
        idempotency_key=body.get("idempotency_key"),
        sla_class=body.get("sla_class"),
    )
    return jsonify(item), 201 if created else 200


@app.get("/api/v1/jobs")
def list_jobs():
    return jsonify(store.list(min(int(request.args.get("limit", 100)), 500)))


@app.get("/api/v1/jobs/<job_id>")
def get_job(job_id):
    item = store.get(job_id)
    if not item:
        return error("job not found", 404)
    item["events"] = store.events(job_id)
    return jsonify(item)


@app.post("/api/v1/jobs/<job_id>/dispatch")
def dispatch(job_id):
    item = store.get(job_id)
    if not item:
        return error("job not found", 404)
    if item["state"] != "QUEUED":
        return error("only QUEUED jobs can be dispatched", 409, state=item["state"])
    status = kube.device_status(DEVICE_NAMESPACE, item["device_id"])
    eligibility = readiness(item["device_id"], status)
    if not eligibility["eligible"]:
        store.add_event(job_id, "DISPATCH_BLOCKED", eligibility)
        return error("device is not eligible", 409, readiness=eligibility)

    policy_request = {
        "request_id": item["id"],
        "subject": {
            "type": "service",
            "id": "dream-job-manager",
        },
        "job": {
            "id": item["id"],
            "command_id": item["command_id"],
            "device_id": item["device_id"],
            "device_kind": item["device_kind"],
            "action": item["action"],
            "parameters": item["parameters"],
            "sla_class": item["sla_class"],
        },
        "context": {
            "readiness": eligibility,
        },
    }
    try:
        policy_result = policy.evaluate(policy_request)
    except (PolicyUnavailable, PolicyProtocolError) as exc:
        store.update_state(
            job_id,
            "QUEUED",
            "POLICY_UNAVAILABLE",
            {"error": str(exc)},
            policy_decision="ERROR",
        )
        return error("policy service unavailable; dispatch blocked", 503)

    if policy_result["decision"] == "DENY":
        reason = "; ".join(policy_result.get("reason_codes", []))
        if not reason:
            reason = "policy denied dispatch"
        denied = store.update_state(
            job_id,
            "FAILED",
            "POLICY_DENIED",
            {"policy": policy_result},
            policy_decision="DENY",
            completed_at=iso_now(),
            last_error=reason,
        )
        return error(
            "policy denied dispatch",
            403,
            job=denied,
            policy=policy_result,
        )

    store.update_state(
        job_id,
        "QUEUED",
        "POLICY_ALLOWED",
        {"policy": policy_result},
        policy_decision="ALLOW",
    )

    envelope, payload = encode_command(
        item["command_id"], item["id"], item["action"], item["parameters"]
    )
    kube.set_requested_action(
        DEVICE_NAMESPACE,
        item["device_id"],
        envelope,
        {"command_id": item["command_id"], "job_id": item["id"], "issued_at": iso_now()},
    )
    updated = store.update_state(
        job_id,
        "DISPATCHED",
        "COMMAND_DISPATCHED",
        {
            "command": payload,
            "readiness": eligibility,
            "policy": policy_result,
        },
        envelope_b64=envelope,
        dispatched_at=iso_now(),
    )
    return jsonify(updated)


@app.post("/api/v1/jobs/<job_id>/cancel")
def cancel(job_id):
    item = store.get(job_id)
    if not item:
        return error("job not found", 404)
    if item["state"] in {"COMPLETED", "FAILED", "CANCELLED"}:
        return error("job is already terminal", 409, state=item["state"])
    if item["state"] in {"DISPATCHED", "ACKNOWLEDGED"}:
        kube.set_requested_action(DEVICE_NAMESPACE, item["device_id"], "NONE")
    return jsonify(
        store.update_state(
            job_id, "CANCELLED", "JOB_CANCELLED", completed_at=iso_now()
        )
    )


def reconcile():
    while True:
        for item in store.active():
            try:
                status = kube.device_status(DEVICE_NAMESPACE, item["device_id"])
                twins = twins_to_map(status)
                if item["state"] == "DISPATCHED":
                    raw_ack = twins.get("commandAck")
                    ack = parse_ack(raw_ack)

                    if ack and ack["command_id"] == item["command_id"]:
                        if ack["status"] == "succeeded":
                            kube.set_requested_action(
                                DEVICE_NAMESPACE,
                                item["device_id"],
                                "NONE",
                            )
                            store.update_state(
                                item["id"],
                                "ACKNOWLEDGED",
                                "COMMAND_ACKNOWLEDGED",
                                {
                                    "commandAck": raw_ack,
                                    "decoded_ack": ack,
                                },
                            )

                            # Re-read the job as ACKNOWLEDGED during the next
                            # pass. This also prevents a valid acknowledgment
                            # and a timeout from being recorded together.
                            continue

                        if ack["status"] == "rejected":
                            reason = str(
                                ack.get("reason") or "device rejected command"
                            )
                            kube.set_requested_action(
                                DEVICE_NAMESPACE,
                                item["device_id"],
                                "NONE",
                            )
                            store.update_state(
                                item["id"],
                                "FAILED",
                                "COMMAND_REJECTED",
                                {
                                    "commandAck": raw_ack,
                                    "decoded_ack": ack,
                                },
                                completed_at=iso_now(),
                                last_error=reason,
                            )
                            continue

                dispatched = item.get("dispatched_at")
                if item["state"] == "DISPATCHED" and dispatched:
                    if (utcnow() - parse_time(dispatched)).total_seconds() > ACK_TIMEOUT_SECONDS:
                        kube.set_requested_action(DEVICE_NAMESPACE, item["device_id"], "NONE")
                        store.update_state(
                            item["id"],
                            "FAILED",
                            "ACK_TIMEOUT",
                            {"timeout_seconds": ACK_TIMEOUT_SECONDS},
                            completed_at=iso_now(),
                            last_error="command acknowledgment timeout",
                        )
                if item["state"] == "ACKNOWLEDGED":
                    complete = False
                    if item["device_kind"] == "robot":
                        complete = twins.get("operatingState") == "READY" and twins.get("currentTask") in (None, "", "NONE")
                    elif item["action"] == "status_refresh":
                        complete = True
                    elif item["action"] in {"pause", "cancel"}:
                        complete = True
                    elif item["action"] == "print_file":
                        complete = twins.get("activeJob") in (None, "", "NONE") and twins.get("progress") in ("100", "100.0", "100.00")
                    if complete:
                        store.update_state(
                            item["id"], "COMPLETED", "JOB_COMPLETED", completed_at=iso_now()
                        )
            except Exception as exc:
                store.add_event(item["id"], "RECONCILE_ERROR", {"error": str(exc)})
        time.sleep(2)


threading.Thread(target=reconcile, name="job-reconciler", daemon=True).start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
