
import os
import time
import uuid
import random
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import requests
from flask import Flask, jsonify, render_template, request
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

APP_NAME = os.getenv("APP_NAME", "web-order-app")
SLA_INTELLIGENCE_URL = os.getenv("SLA_INTELLIGENCE_URL", "")
JOB_MANAGER_URL = os.getenv("JOB_MANAGER_URL", "")
MARKETPLACE_URL = os.getenv("MARKETPLACE_URL", "")
POLICY_MANAGER_URL = os.getenv("POLICY_MANAGER_URL", "")
ONOS_URL = os.getenv("ONOS_URL", "")
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

REQUEST_COUNTER = Counter("maas_web_orders_total", "Total MaaS orders submitted")
SELECTION_LATENCY = Histogram("maas_selection_latency_seconds", "Time spent selecting a site/device")
ACTIVE_ORDERS = Gauge("maas_active_orders", "Number of active orders in memory")

ORDERS: Dict[str, Dict[str, Any]] = {}

EDGE_SITES = {
    "NMSU": {
        "label": "NMSU",
        "rtt_ms": 64,
        "devices": [
            {"id": "NMSU-P1", "type": "3d_printer", "model": "Ender-3", "health": 0.88, "queue": 1, "availability": 0.92, "progress": 0, "status": "idle"},
            {"id": "NMSU-R1", "type": "robot_arm", "model": "Robot Arm", "health": 0.84, "queue": 1, "availability": 0.90, "progress": 0, "status": "idle"},
        ],
    },
    "NMT": {
        "label": "NMT",
        "rtt_ms": 112,
        "devices": [
            {"id": "NMT-P1", "type": "3d_printer", "model": "Prusa/Ender", "health": 0.78, "queue": 2, "availability": 0.82, "progress": 0, "status": "idle"},
            {"id": "NMT-R1", "type": "robot_arm", "model": "Robot Arm", "health": 0.74, "queue": 2, "availability": 0.80, "progress": 0, "status": "idle"},
        ],
    },
    "NTU": {
        "label": "NTU",
        "rtt_ms": 192,
        "devices": [
            {"id": "NTU-P1", "type": "3d_printer", "model": "Formlabs Fuse", "health": 0.83, "queue": 2, "availability": 0.86, "progress": 0, "status": "idle"},
            {"id": "NTU-R1", "type": "robot_arm", "model": "Robot Arm", "health": 0.81, "queue": 1, "availability": 0.84, "progress": 0, "status": "idle"},
        ],
    },
}

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def client_penalty(client_location: str, site: str) -> float:
    if client_location == "New Mexico / Southwest":
        return {"NMSU": 0.00, "NMT": 0.04, "NTU": 0.18}.get(site, 0.1)
    if client_location == "California / West Coast":
        return {"NMSU": 0.06, "NMT": 0.08, "NTU": 0.03}.get(site, 0.1)
    if client_location == "East Coast":
        return {"NMSU": 0.12, "NMT": 0.13, "NTU": 0.14}.get(site, 0.1)
    return 0.08

def score_candidate(site_name: str, device: Dict[str, Any], payload: Dict[str, Any]) -> float:
    rtt_ms = EDGE_SITES[site_name]["rtt_ms"]
    health = float(device["health"])
    availability = float(device["availability"])
    queue = float(device["queue"])

    rtt_score = max(0.0, 1.0 - (rtt_ms / 300.0))
    queue_score = max(0.0, 1.0 - (queue / 8.0))
    wan_penalty = client_penalty(payload.get("client_location", ""), site_name)

    sla = payload.get("sla_tier", "standard")
    if sla == "urgent":
        weights = {"health": 0.30, "availability": 0.20, "queue": 0.20, "rtt": 0.30}
    elif sla == "cost_optimized":
        weights = {"health": 0.25, "availability": 0.35, "queue": 0.30, "rtt": 0.10}
    else:
        weights = {"health": 0.30, "availability": 0.25, "queue": 0.25, "rtt": 0.20}

    score = (
        weights["health"] * health
        + weights["availability"] * availability
        + weights["queue"] * queue_score
        + weights["rtt"] * rtt_score
        - wan_penalty
    )
    return round(max(0.0, min(score, 1.0)), 3)

def select_device(payload: Dict[str, Any]) -> Dict[str, Any]:
    device_type = payload.get("device_type", "3d_printer")
    routing_mode = payload.get("routing_mode", "AUTO")
    preferred_site = payload.get("preferred_site", "NMSU")

    candidates: List[Dict[str, Any]] = []

    for site_name, site in EDGE_SITES.items():
        if routing_mode == "SITE" and site_name != preferred_site:
            continue

        for device in site["devices"]:
            if device["type"] != device_type:
                continue

            scored = {
                **device,
                "site": site_name,
                "rtt_ms": site["rtt_ms"],
                "score": score_candidate(site_name, device, payload),
            }
            candidates.append(scored)

    if not candidates:
        raise ValueError("No eligible device found for the selected policy/device type.")

    return sorted(candidates, key=lambda x: x["score"], reverse=True)[0]

def forward_to_service(url: str, path: str, payload: Dict[str, Any], timeout: int = 5) -> Optional[Dict[str, Any]]:
    if not url:
        return None
    try:
        resp = requests.post(url.rstrip("/") + path, json=payload, timeout=timeout)
        return {"status_code": resp.status_code, "body": resp.json() if resp.content else {}}
    except Exception as exc:
        return {"error": str(exc)}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"service": APP_NAME, "status": "ok", "demo_mode": DEMO_MODE, "time": now_iso()})

@app.route("/api/sites", methods=["GET"])
def sites():
    return jsonify({"sites": EDGE_SITES})

@app.route("/api/orders", methods=["GET"])
def list_orders():
    return jsonify({"orders": list(ORDERS.values())})

@app.route("/api/orders/<order_id>", methods=["GET"])
def get_order(order_id):
    order = ORDERS.get(order_id)
    if not order:
        return jsonify({"error": "order not found"}), 404
    return jsonify(order)

@app.route("/api/orders", methods=["POST"])
def submit_order():
    start = time.time()
    REQUEST_COUNTER.inc()

    payload = request.get_json(force=True, silent=True) or {}
    required = ["client_location", "device_type", "routing_mode", "sla_tier"]
    missing = [k for k in required if not payload.get(k)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    try:
        selected = select_device(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    order_id = f"maas-{uuid.uuid4().hex[:10]}"
    order = {
        "order_id": order_id,
        "created_at": now_iso(),
        "state": "PLANNED",
        "request": payload,
        "selected": selected,
        "selection_logic": {
            "mode": payload.get("routing_mode"),
            "preferred_site": payload.get("preferred_site"),
            "policy": "AUTO scores all eligible sites; SITE restricts selection to the preferred site",
            "score": selected["score"],
            "decision_inputs": {
                "health": selected["health"],
                "queue": selected["queue"],
                "rtt_ms": selected["rtt_ms"],
                "availability": selected["availability"],
            },
        },
        "downstream": {},
    }

    if not DEMO_MODE:
        order["downstream"]["job_manager"] = forward_to_service(JOB_MANAGER_URL, "/api/jobs", order)
        order["downstream"]["policy_manager"] = forward_to_service(POLICY_MANAGER_URL, "/api/policies/evaluate", order)
        order["downstream"]["sla_intelligence"] = forward_to_service(SLA_INTELLIGENCE_URL, "/api/score", order)

    ORDERS[order_id] = order
    ACTIVE_ORDERS.set(len(ORDERS))
    SELECTION_LATENCY.observe(time.time() - start)

    return jsonify(order), 201

@app.route("/api/orders/<order_id>/dispatch", methods=["POST"])
def dispatch_order(order_id):
    order = ORDERS.get(order_id)
    if not order:
        return jsonify({"error": "order not found"}), 404
    order["state"] = "DISPATCHED"
    order["dispatched_at"] = now_iso()

    if not DEMO_MODE:
        order["downstream"]["job_manager_dispatch"] = forward_to_service(JOB_MANAGER_URL, f"/api/jobs/{order_id}/dispatch", order)
        order["downstream"]["onos"] = forward_to_service(ONOS_URL, "/api/onos/intents", order)

    return jsonify(order)

@app.route("/api/orders/<order_id>/simulate-progress", methods=["POST"])
def simulate_progress(order_id):
    order = ORDERS.get(order_id)
    if not order:
        return jsonify({"error": "order not found"}), 404

    progress = int(order.get("progress", 0))
    progress = min(100, progress + random.randint(10, 25))
    order["progress"] = progress
    order["state"] = "COMPLETED" if progress >= 100 else "PRINTING"
    order["updated_at"] = now_iso()
    return jsonify(order)

@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
