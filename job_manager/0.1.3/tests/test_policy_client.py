import io
import json
import unittest
import urllib.error
from unittest.mock import patch

from policy_client import (
    PolicyClient,
    PolicyProtocolError,
    PolicyUnavailable,
)


class FakeResponse:
    def __init__(self, payload):
        self.body = io.BytesIO(json.dumps(payload).encode())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return self.body.read(limit)


class PolicyClientTests(unittest.TestCase):
    def setUp(self):
        self.client = PolicyClient("http://policy:8090", 1)
        self.payload = {"request_id": "job-1"}

    @patch("urllib.request.urlopen")
    def test_accepts_allow_decision(self, urlopen):
        urlopen.return_value = FakeResponse(
            {
                "decision": "ALLOW",
                "decision_id": "decision-1",
                "policy_version": "test-1",
            }
        )

        result = self.client.evaluate(self.payload)

        self.assertEqual(result["decision"], "ALLOW")

    @patch("urllib.request.urlopen")
    def test_accepts_deny_decision(self, urlopen):
        urlopen.return_value = FakeResponse(
            {
                "decision": "DENY",
                "decision_id": "decision-2",
                "policy_version": "test-1",
            }
        )

        result = self.client.evaluate(self.payload)

        self.assertEqual(result["decision"], "DENY")

    @patch("urllib.request.urlopen")
    def test_fails_closed_when_service_is_unavailable(self, urlopen):
        urlopen.side_effect = urllib.error.URLError("connection refused")

        with self.assertRaises(PolicyUnavailable):
            self.client.evaluate(self.payload)

    @patch("urllib.request.urlopen")
    def test_rejects_invalid_policy_response(self, urlopen):
        urlopen.return_value = FakeResponse(
            {
                "decision": "MAYBE",
                "decision_id": "decision-3",
                "policy_version": "test-1",
            }
        )

        with self.assertRaises(PolicyProtocolError):
            self.client.evaluate(self.payload)


if __name__ == "__main__":
    unittest.main()
