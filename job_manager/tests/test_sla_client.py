import io
import json
import unittest
import urllib.error
from unittest.mock import patch

from sla_client import SLAClient, SLAProtocolError, SLAUnavailable


class FakeResponse:
    def __init__(self, payload):
        self.body = io.BytesIO(json.dumps(payload).encode())
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, limit):
        return self.body.read(limit)


class SLAClientTests(unittest.TestCase):
    def setUp(self):
        self.client = SLAClient("http://sla:8070", 1)

    @patch("urllib.request.urlopen")
    def test_accepts_admit(self, urlopen):
        urlopen.return_value = FakeResponse({"decision": "ADMIT", "decision_id": "sla-1", "sla_version": "test-1"})
        self.assertEqual(self.client.evaluate({"request_id": "job-1"})["decision"], "ADMIT")

    @patch("urllib.request.urlopen")
    def test_accepts_reject(self, urlopen):
        urlopen.return_value = FakeResponse({"decision": "REJECT", "decision_id": "sla-2", "sla_version": "test-1"})
        self.assertEqual(self.client.evaluate({"request_id": "job-1"})["decision"], "REJECT")

    @patch("urllib.request.urlopen")
    def test_fails_closed_when_unavailable(self, urlopen):
        urlopen.side_effect = urllib.error.URLError("refused")
        with self.assertRaises(SLAUnavailable):
            self.client.evaluate({"request_id": "job-1"})

    @patch("urllib.request.urlopen")
    def test_rejects_invalid_response(self, urlopen):
        urlopen.return_value = FakeResponse({"decision": "MAYBE", "decision_id": "sla-3", "sla_version": "test-1"})
        with self.assertRaises(SLAProtocolError):
            self.client.evaluate({"request_id": "job-1"})


if __name__ == "__main__":
    unittest.main()
