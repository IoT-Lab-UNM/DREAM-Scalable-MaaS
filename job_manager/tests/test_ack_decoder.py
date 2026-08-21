import base64
import json
import unittest

from core import ack_matches, parse_ack


def encode_b64url(payload):
    raw = json.dumps(payload, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return "b64url:" + encoded


class AckDecoderTests(unittest.TestCase):
    def test_decodes_succeeded_b64url_ack(self):
        value = encode_b64url(
            {
                "command_id": "job-123",
                "job_id": "123",
                "status": "succeeded",
            }
        )

        parsed = parse_ack(value)

        self.assertEqual(parsed["command_id"], "job-123")
        self.assertEqual(parsed["status"], "succeeded")
        self.assertTrue(ack_matches("job-123", value))

    def test_decodes_rejected_ack_and_reason(self):
        value = encode_b64url(
            {
                "command_id": "job-456",
                "status": "rejected",
                "reason": "physical start not confirmed",
            }
        )

        parsed = parse_ack(value)

        self.assertEqual(parsed["status"], "rejected")
        self.assertEqual(parsed["reason"], "physical start not confirmed")

    def test_decodes_in_progress_ack(self):
        value = encode_b64url(
            {
                "command_id": "job-789",
                "status": "in_progress",
            }
        )

        self.assertEqual(parse_ack(value)["status"], "in_progress")

    def test_preserves_legacy_raw_json_match(self):
        value = json.dumps(
            {
                "command_id": "cmd-1",
                "state": "sent",
            }
        )

        self.assertTrue(ack_matches("cmd-1", value))

    def test_rejects_wrong_command_id(self):
        value = encode_b64url(
            {
                "command_id": "different-command",
                "status": "succeeded",
            }
        )

        self.assertFalse(ack_matches("expected-command", value))

    def test_rejects_malformed_ack(self):
        self.assertIsNone(parse_ack("b64url:not-valid-json"))
        self.assertIsNone(parse_ack("NONE"))
        self.assertIsNone(parse_ack(json.dumps({"status": "succeeded"})))


if __name__ == "__main__":
    unittest.main()
