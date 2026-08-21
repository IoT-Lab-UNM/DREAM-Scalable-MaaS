import json
import tempfile
import unittest
from pathlib import Path

from engine import (
    PolicyConfigurationError,
    PolicyEngine,
    PolicyRequestError,
)


POLICY = {
    "version": "test-1",
    "default_effect": "DENY",
    "rules": [
        {
            "id": "allow-safe-refresh",
            "effect": "ALLOW",
            "match": {
                "device_ids": ["ender3-printer-01"],
                "actions": ["status_refresh"],
                "sla_classes": ["validation"],
                "require_eligible": True,
            },
            "reason_codes": ["safe_validation_action"],
        },
        {
            "id": "deny-physical",
            "effect": "DENY",
            "match": {"actions": ["print_file", "motor_enable"]},
            "reason_codes": ["physical_action_not_authorized"],
        },
    ],
}


def request(action="status_refresh", sla_class="validation", eligible=True):
    return {
        "request_id": "job-1",
        "job": {
            "id": "job-1",
            "command_id": "command-1",
            "device_id": "ender3-printer-01",
            "device_kind": "printer",
            "action": action,
            "parameters": {},
            "sla_class": sla_class,
        },
        "context": {"readiness": {"eligible": eligible}},
    }


class PolicyEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "policies.json"
        self.path.write_text(json.dumps(POLICY))
        self.engine = PolicyEngine(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_allows_safe_validation_refresh(self):
        result = self.engine.evaluate(request())

        self.assertEqual(result["decision"], "ALLOW")
        self.assertEqual(result["matched_policy"], "allow-safe-refresh")

    def test_denies_physical_action(self):
        result = self.engine.evaluate(request(action="print_file"))

        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["matched_policy"], "deny-physical")

    def test_default_denies_wrong_sla_class(self):
        result = self.engine.evaluate(request(sla_class="blocked-validation"))

        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["matched_policy"], "default")

    def test_default_denies_ineligible_device(self):
        result = self.engine.evaluate(request(eligible=False))

        self.assertEqual(result["decision"], "DENY")

    def test_rejects_malformed_request(self):
        with self.assertRaises(PolicyRequestError):
            self.engine.evaluate({"job": {}})

    def test_rejects_malformed_policy_rule(self):
        invalid = dict(POLICY)
        invalid["rules"] = [
            {
                "id": "invalid",
                "effect": "ALLOW",
                "match": {"actions": "status_refresh"},
            }
        ]
        self.path.write_text(json.dumps(invalid))

        with self.assertRaises(PolicyConfigurationError):
            self.engine.policy()


if __name__ == "__main__":
    unittest.main()
