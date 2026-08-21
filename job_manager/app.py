import os
import threading
import time

from flask import Flask, jsonify, request

from core import DEVICE_PROFILES, ack_matches, encode_command, iso_now, readiness, twins_to_map
from kubeedge_client import KubeEdgeClient
from store import JobStore


DB_PATH = os.getenv("JOB_DB_PATH", "/data/jobs.db")
DEVICE_NAMESPACE = os.getenv("DEVICE_NAMESPACE", "default")
ACK_TIMEOUT_SECONDS = int(os.getenv("ACK_TIMEOUT_SECONDS", "60"))

app = Flask(__name__)
store = JobStore(DB_PATH)
kube = KubeEdgeClient()


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
        {"command": payload, "readiness": eligibility},
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
                if item["state"] == "DISPATCHED" and ack_matches(item["command_id"], twins.get("commandAck")):
                    kube.set_requested_action(DEVICE_NAMESPACE, item["device_id"], "NONE")
                    store.update_state(
                        item["id"],
                        "ACKNOWLEDGED",
                        "COMMAND_ACKNOWLEDGED",
                        {"commandAck": twins.get("commandAck")},
                    )
                dispatched = item.get("dispatched_at")
                if item["state"] == "DISPATCHED" and dispatched:
                    from core import parse_time, utcnow
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
