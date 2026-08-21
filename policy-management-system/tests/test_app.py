import unittest
from unittest.mock import patch

try:
    import app as policy_app
except ModuleNotFoundError as exc:
    if exc.name != "flask":
        raise
    raise unittest.SkipTest("Flask is not installed in this test environment")


class PolicyAppTests(unittest.TestCase):
    def setUp(self):
        self.client = policy_app.app.test_client()

    @patch.object(policy_app.engine, "evaluate")
    def test_evaluate_returns_auditable_decision(self, evaluate):
        evaluate.return_value = {
            "decision": "ALLOW",
            "matched_policy": "allow-test",
            "reason_codes": ["test"],
            "policy_version": "test-1",
        }
        response = self.client.post(
            "/api/v1/policy/evaluate",
            json={
                "request_id": "job-1",
                "job": {
                    "id": "job-1",
                    "command_id": "command-1",
                    "device_id": "ender3-printer-01",
                    "action": "status_refresh",
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        value = response.get_json()
        self.assertEqual(value["decision"], "ALLOW")
        self.assertTrue(value["decision_id"])
        self.assertTrue(value["evaluated_at"])

    @patch.object(policy_app.engine, "policy")
    def test_legacy_read_endpoints_remain_available(self, policy):
        policy.return_value = {
            "version": "test-1",
            "default_effect": "DENY",
            "rules": [],
        }

        self.assertEqual(self.client.get("/policies").status_code, 200)
        self.assertEqual(self.client.get("/readyz").status_code, 200)


if __name__ == "__main__":
    unittest.main()
