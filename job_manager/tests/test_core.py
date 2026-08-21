import json
import unittest
from datetime import datetime, timezone

from core import ack_matches, encode_command, readiness


def status(device_id, twins, state="online"):
    return {
        "metadata": {"name": device_id},
        "status": {
            "state": state,
            "twins": [
                {"propertyName": key, "reported": {"value": value}}
                for key, value in twins.items()
            ],
        },
    }


class CoreTests(unittest.TestCase):
    def test_command_envelope(self):
        encoded, payload = encode_command(
            "c1",
            "j1",
            "status_refresh",
            {},
        )

        self.assertTrue(encoded.startswith("{"))
        self.assertEqual(json.loads(encoded), payload)
        self.assertEqual(payload["command_id"], "c1")

    def test_robot_ready(self):
        now = datetime(2026, 8, 21, 16, 39, 10, tzinfo=timezone.utc)
        obj = status("freenove-arm-01", {
            "availability": "ONLINE", "fault": "NONE", "operatingState": "READY",
            "currentTask": "NONE", "lastUpdate": "2026-08-21T16:39:00Z"
        })
        self.assertTrue(readiness("freenove-arm-01", obj, now)["eligible"])

    def test_stale_printer_blocked(self):
        now = datetime(2026, 8, 21, 16, 40, 0, tzinfo=timezone.utc)
        obj = status("ender3-printer-01", {
            "availability": "ONLINE", "fault": "NONE", "printerState": "Operational",
            "activeJob": "NONE", "lastUpdate": "2026-08-21T16:38:50Z"
        })
        result = readiness("ender3-printer-01", obj, now)
        self.assertFalse(result["eligible"])
        self.assertIn("twin_stale", result["reasons"])

    def test_ack_match(self):
        self.assertTrue(ack_matches("cmd-1", json.dumps({"command_id": "cmd-1", "state": "sent"})))
        self.assertFalse(ack_matches("cmd-1", "NONE"))


if __name__ == "__main__":
    unittest.main()
