import json
import logging
import os
import threading

from flask import Flask, jsonify, request

from engine import SLAEngine, SLARequestError, iso_now, load_configuration


CONFIG_PATH = os.getenv("SLA_CONFIG_PATH", "/config/sla-classes.json")
configuration = load_configuration(CONFIG_PATH)
engine = SLAEngine(configuration)
app = Flask(__name__)
lock = threading.Lock()
latest_telemetry = {}
counters = {"evaluations": 0, "admitted": 0, "rejected": 0, "telemetry_samples": 0}
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


def error(message, status=400):
    return jsonify({"error": message}), status


@app.get("/healthz")
def health():
    return jsonify({"status": "ok", "service": "dream-sla-intelligence", "sla_version": configuration["version"]})


@app.get("/readyz")
def ready():
    return health()


@app.get("/api/v1/sla/classes")
def classes():
    return jsonify({"version": configuration["version"], "classes": configuration["classes"]})


@app.post("/api/v1/telemetry")
def ingest_telemetry():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return error("request must be a JSON object")
    device_id = str(body.get("device_id") or "").strip()
    metrics = body.get("metrics")
    if not device_id or not isinstance(metrics, dict):
        return error("device_id and metrics are required")
    accepted = {"rtt_ms", "loss_percent", "jitter_ms", "queue_depth"}
    cleaned = {}
    for name, value in metrics.items():
        if name not in accepted:
            continue
        try:
            cleaned[name] = float(value)
        except (TypeError, ValueError):
            return error(f"metric {name} must be numeric")
    sample = {"device_id": device_id, "site_id": body.get("site_id"), "observed_at": body.get("observed_at") or iso_now(), "metrics": cleaned}
    with lock:
        latest_telemetry[device_id] = sample
        counters["telemetry_samples"] += 1
    return jsonify(sample), 202


@app.get("/api/v1/telemetry/<device_id>")
def get_telemetry(device_id):
    with lock:
        sample = latest_telemetry.get(device_id)
    if sample is None:
        return error("no telemetry for device", 404)
    return jsonify(sample)


@app.post("/api/v1/sla/evaluate")
def evaluate():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return error("request must be a JSON object")
    device_id = str((body.get("job") or {}).get("device_id") or "")
    inline = (body.get("context") or {}).get("telemetry")
    with lock:
        telemetry = inline if isinstance(inline, dict) else latest_telemetry.get(device_id)
    try:
        result = engine.evaluate(body, telemetry)
    except SLARequestError as exc:
        return error(str(exc))
    with lock:
        counters["evaluations"] += 1
        counters["admitted" if result["decision"] == "ADMIT" else "rejected"] += 1
    app.logger.info(json.dumps({"event": "SLA_DECISION", **result}, separators=(",", ":")))
    return jsonify(result)


@app.get("/api/v1/kpis")
def kpis():
    with lock:
        result = dict(counters)
        result["devices_with_telemetry"] = len(latest_telemetry)
    result["admission_rate"] = round(result["admitted"] / result["evaluations"], 4) if result["evaluations"] else None
    result["sla_version"] = configuration["version"]
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8070)
