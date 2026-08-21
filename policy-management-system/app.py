import json
import logging
import os
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request

from engine import (
    PolicyConfigurationError,
    PolicyEngine,
    PolicyRequestError,
)


POLICY_PATH = os.getenv("POLICY_PATH", "/config/policies.json")

app = Flask(__name__)
engine = PolicyEngine(POLICY_PATH)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


def iso_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@app.get("/healthz")
def health():
    try:
        policy = engine.policy()
    except PolicyConfigurationError as exc:
        return jsonify({"status": "error", "error": str(exc)}), 503
    return jsonify(
        {
            "service": "dream-policy-management",
            "status": "ok",
            "policy_version": policy["version"],
        }
    )


@app.get("/api/v1/policies")
def policies():
    try:
        return jsonify(engine.policy())
    except PolicyConfigurationError as exc:
        return jsonify({"error": str(exc)}), 503


@app.get("/policies")
def legacy_policies():
    """Read-only compatibility alias for the original prototype API."""
    return policies()


@app.get("/readyz")
def ready():
    """Compatibility readiness endpoint used by the original manifest."""
    return health()


@app.post("/api/v1/policy/evaluate")
def evaluate():
    body = request.get_json(silent=True)
    try:
        result = engine.evaluate(body)
    except PolicyRequestError as exc:
        return jsonify({"error": str(exc)}), 400
    except PolicyConfigurationError as exc:
        return jsonify({"error": str(exc)}), 503

    result.update(
        {
            "decision_id": str(uuid.uuid4()),
            "request_id": body.get("request_id"),
            "evaluated_at": iso_now(),
        }
    )
    app.logger.info(
        json.dumps(
            {
                "event": "POLICY_DECISION",
                **result,
                "job_id": body["job"]["id"],
                "command_id": body["job"]["command_id"],
                "device_id": body["job"]["device_id"],
                "action": body["job"]["action"],
            },
            separators=(",", ":"),
        )
    )
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090)
