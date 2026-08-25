import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

import requests
from flask import Flask, jsonify, render_template, request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

APP_NAME = os.getenv("APP_NAME", "dream-web-order-app")
JOB_MANAGER_URL = os.getenv(
    "JOB_MANAGER_URL",
    "http://dream-job-manager.dream-maas.svc.cluster.local:8080",
).rstrip("/")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "8"))

REQUEST_COUNTER = Counter(
    "maas_web_actions_total",
    "Total workshop actions submitted through the Web Order App",
    ["device_id", "action", "result"],
)
REQUEST_LATENCY = Histogram(
    "maas_web_action_latency_seconds",
    "Web Order App request latency to Job Manager",
    ["action"],
)

PRINTER_ID = "ender3-printer-01"
ROBOT_ID = "freenove-arm-01"

# Fixed workshop actions only. No arbitrary coordinates are accepted from the browser.
WORKSHOP_ACTIONS: Dict[str, Dict[str, Any]] = {
    "printer_status": {
        "label": "Refresh Printer Status",
        "device_id": PRINTER_ID,
        "action": "status_refresh",
        "parameters": {},
        "sla_class": "validation",
        "physical": False,
    },
    "printer_cube": {
        "label": "Print Calibration Cube",
        "device_id": PRINTER_ID,
        "action": "print_file",
        "parameters": {
            "artifact_id": "workshop-calibration-cube-20mm",
            "path": "calibration_cube_20mm.gcode",
            "confirmPhysicalStart": True,
        },
        "sla_class": "validation",
        "physical": True,
    },
    "robot_home": {
        "label": "Sensor Home",
        "device_id": ROBOT_ID,
        "action": "sensor_home",
        "parameters": {"confirmPhysicalMotion": True},
        "sla_class": "validation",
        "physical": True,
    },
    "robot_move_home": {
        "label": "Move to Demo Home",
        "device_id": ROBOT_ID,
        "action": "move_xyz",
        "parameters": {
            "x": 0,
            "y": 200,
            "z": 45,
            "confirmPhysicalMotion": True,
        },
        "sla_class": "validation",
        "physical": True,
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def jm_request(method: str, path: str, **kwargs) -> Tuple[Dict[str, Any], int]:
    url = f"{JOB_MANAGER_URL}{path}"
    try:
        resp = requests.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
        try:
            body = resp.json() if resp.content else {}
        except ValueError:
            body = {"raw": resp.text}
        return body, resp.status_code
    except requests.RequestException as exc:
        return {"error": "job_manager_unreachable", "detail": str(exc), "url": url}, 502


def simplify_device(body: Dict[str, Any]) -> Dict[str, Any]:
    readiness = body.get("readiness") or {}
    twins = readiness.get("twins") or {}
    return {
        "device_id": body.get("device_id"),
        "state": body.get("state"),
        "eligible": readiness.get("eligible"),
        "freshness_age_seconds": readiness.get("freshness_age_seconds"),
        "freshness_limit_seconds": readiness.get("freshness_limit_seconds"),
        "reasons": readiness.get("reasons", []),
        "twins": twins,
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def health():
    jm_body, jm_status = jm_request("GET", "/healthz")
    return jsonify({
        "service": APP_NAME,
        "status": "ok" if jm_status < 500 else "degraded",
        "job_manager_url": JOB_MANAGER_URL,
        "job_manager": jm_body,
        "time": now_iso(),
    }), 200 if jm_status < 500 else 503


@app.get("/api/devices")
def devices():
    output = {}
    overall = 200
    for device_id in (PRINTER_ID, ROBOT_ID):
        body, status = jm_request("GET", f"/api/v1/devices/{device_id}")
        if status >= 400:
            overall = 207
            output[device_id] = {"error": body, "http_status": status}
        else:
            output[device_id] = simplify_device(body)
    return jsonify({"devices": output, "time": now_iso()}), overall


@app.get("/api/actions")
def actions():
    safe_view = {
        key: {
            "label": value["label"],
            "device_id": value["device_id"],
            "action": value["action"],
            "physical": value["physical"],
        }
        for key, value in WORKSHOP_ACTIONS.items()
    }
    return jsonify({"actions": safe_view})


@app.post("/api/actions/<action_key>")
def run_action(action_key: str):
    spec = WORKSHOP_ACTIONS.get(action_key)
    if spec is None:
        return jsonify({"error": "unsupported_workshop_action"}), 404

    started = time.time()
    idempotency_key = f"web-{action_key}-{int(time.time() * 1000)}"
    create_payload = {
        "device_id": spec["device_id"],
        "action": spec["action"],
        "parameters": spec["parameters"],
        "idempotency_key": idempotency_key,
        "sla_class": spec["sla_class"],
    }

    create_body, create_status = jm_request("POST", "/api/v1/jobs", json=create_payload)
    if create_status >= 300:
        REQUEST_COUNTER.labels(spec["device_id"], spec["action"], "create_failed").inc()
        REQUEST_LATENCY.labels(spec["action"]).observe(time.time() - started)
        return jsonify({
            "stage": "create",
            "request": create_payload,
            "job_manager": create_body,
        }), create_status

    job_id = create_body.get("id")
    if not job_id:
        REQUEST_COUNTER.labels(spec["device_id"], spec["action"], "invalid_create_response").inc()
        return jsonify({"error": "job_manager_returned_no_job_id", "job": create_body}), 502

    dispatch_body, dispatch_status = jm_request(
        "POST", f"/api/v1/jobs/{job_id}/dispatch"
    )

    result = "dispatched" if dispatch_status < 300 else "dispatch_failed"
    REQUEST_COUNTER.labels(spec["device_id"], spec["action"], result).inc()
    REQUEST_LATENCY.labels(spec["action"]).observe(time.time() - started)

    return jsonify({
        "action_key": action_key,
        "label": spec["label"],
        "physical": spec["physical"],
        "job_id": job_id,
        "created": create_body,
        "dispatch": dispatch_body,
        "dispatch_http_status": dispatch_status,
        "submitted_at": now_iso(),
    }), 200 if dispatch_status < 300 else dispatch_status


@app.get("/api/jobs/<job_id>")
def job(job_id: str):
    body, status = jm_request("GET", f"/api/v1/jobs/{job_id}")
    return jsonify(body), status


@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
