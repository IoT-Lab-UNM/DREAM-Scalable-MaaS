import os
import unittest

os.environ["SLA_CONFIG_PATH"] = os.path.join(os.path.dirname(__file__), "..", "sla-classes.json")

from app import app


class SLAAppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health_and_classes(self):
        self.assertEqual(self.client.get("/healthz").status_code, 200)
        self.assertIn("validation", self.client.get("/api/v1/sla/classes").get_json()["classes"])

    def test_ingest_and_evaluate(self):
        response = self.client.post("/api/v1/telemetry", json={"device_id": "ender3-printer-01", "metrics": {"rtt_ms": 20, "loss_percent": 0, "jitter_ms": 2, "queue_depth": 0}})
        self.assertEqual(response.status_code, 202)
        response = self.client.post("/api/v1/sla/evaluate", json={"request_id": "job-app", "job": {"id": "job-app", "command_id": "cmd-app", "device_id": "ender3-printer-01", "sla_class": "validation"}, "context": {"readiness": {"eligible": True, "freshness_age_seconds": 2}}})
        self.assertEqual(response.get_json()["decision"], "ADMIT")


if __name__ == "__main__":
    unittest.main()
