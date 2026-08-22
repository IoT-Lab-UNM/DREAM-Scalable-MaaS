import unittest
from datetime import datetime, timezone

from engine import SLAEngine


CONFIG = {
    "version": "test-1",
    "classes": {
        "validation": {
            "max_freshness_age_seconds": 30,
            "min_score": 70,
            "require_network_telemetry": False,
            "max_telemetry_age_seconds": 60,
            "max_rtt_ms": 500,
            "max_loss_percent": 5,
            "max_jitter_ms": 100,
            "max_queue_depth": 1,
        },
        "priority": {
            "max_freshness_age_seconds": 10,
            "min_score": 85,
            "require_network_telemetry": True,
            "max_telemetry_age_seconds": 20,
            "max_rtt_ms": 100,
            "max_loss_percent": 1,
            "max_jitter_ms": 20,
            "max_queue_depth": 0,
        },
    },
}


class SLAEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = SLAEngine(CONFIG)
        self.request = {
            "request_id": "job-1",
            "job": {"id": "job-1", "command_id": "command-1", "device_id": "ender3-printer-01", "sla_class": "validation"},
            "context": {"readiness": {"eligible": True, "freshness_age_seconds": 5}},
        }

    def test_admits_safe_validation_without_network_telemetry(self):
        result = self.engine.evaluate(self.request)
        self.assertEqual(result["decision"], "ADMIT")
        self.assertIn("sla_targets_met", result["reason_codes"])

    def test_rejects_ineligible_device(self):
        self.request["context"]["readiness"]["eligible"] = False
        result = self.engine.evaluate(self.request)
        self.assertEqual(result["decision"], "REJECT")
        self.assertIn("device_not_eligible", result["reason_codes"])

    def test_rejects_unknown_class(self):
        self.request["job"]["sla_class"] = "gold"
        self.assertEqual(self.engine.evaluate(self.request)["decision"], "REJECT")

    def test_priority_requires_network_telemetry(self):
        self.request["job"]["sla_class"] = "priority"
        result = self.engine.evaluate(self.request)
        self.assertIn("network_telemetry_required", result["reason_codes"])

    def test_rejects_threshold_breach(self):
        telemetry = {"observed_at": "2026-08-22T00:00:00Z", "metrics": {"rtt_ms": 600, "loss_percent": 0, "jitter_ms": 0, "queue_depth": 0}}
        result = self.engine.evaluate(self.request, telemetry, datetime(2026, 8, 22, 0, 0, 5, tzinfo=timezone.utc))
        self.assertIn("rtt_ms_slo_exceeded", result["reason_codes"])


if __name__ == "__main__":
    unittest.main()
