import json
import os
import re
import signal
import sqlite3
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from freenove_protocol import FreenoveClient, format_move, format_servo


def now():
    return datetime.now(timezone.utc).isoformat()


class Adapter:
    def __init__(self):
        self.site = os.getenv("SITE_ID", "unm-lab")
        self.device = os.getenv("DEVICE_ID", "freenove-arm-01")
        self.robot_host = os.environ["ROBOT_HOST"]
        self.robot_port = int(os.getenv("ROBOT_PORT", "5000"))
        self.mqtt_host = os.getenv("MQTT_HOST", "127.0.0.1")
        self.mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
        self.prefix = f"dream/v1/sites/{self.site}/devices/{self.device}"
        self.topic_command = f"{self.prefix}/commands"
        self.topic_ack = f"{self.prefix}/acks"
        self.topic_state = f"{self.prefix}/state"
        self.allow_s13 = os.getenv("ALLOW_S13", "false").lower() == "true"
        self.bounds = {
            "x": (float(os.getenv("X_MIN", "-100")), float(os.getenv("X_MAX", "100"))),
            "y": (float(os.getenv("Y_MIN", "150")), float(os.getenv("Y_MAX", "250"))),
            "z": (float(os.getenv("Z_MIN", "0")), float(os.getenv("Z_MAX", "120"))),
        }
        self.queue_count = None
        self.last_line = None
        self.last_error = None
        self.stop_event = threading.Event()
        os.makedirs("/data", exist_ok=True)
        self.db = sqlite3.connect("/data/commands.db", check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS commands (command_id TEXT PRIMARY KEY, status TEXT, updated TEXT)")
        self.db.commit()

        self.robot = FreenoveClient(self.robot_host, self.robot_port, self.on_robot_line, self.on_robot_state)
        self.mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"robot-adapter-{self.device}")
        user = os.getenv("MQTT_USERNAME")
        if user:
            self.mqtt.username_pw_set(user, os.getenv("MQTT_PASSWORD"))
        self.mqtt.on_connect = self.on_mqtt_connect
        self.mqtt.on_message = self.on_mqtt_message

    def publish(self, topic, payload, retain=False):
        payload.setdefault("schema_version", "1.0")
        payload.setdefault("site_id", self.site)
        payload.setdefault("gateway", "robotarm")
        payload.setdefault("device_id", self.device)
        payload.setdefault("device_type", "freenove-arm")
        payload.setdefault("timestamp", now())
        self.mqtt.publish(topic, json.dumps(payload, separators=(",", ":")), qos=1, retain=retain)

    def ack(self, command_id, job_id, status, **extra):
        body = {"command_id": command_id, "job_id": job_id, "status": status, **extra}
        self.publish(self.topic_ack, body)
        self.db.execute("INSERT OR REPLACE INTO commands VALUES (?,?,?)", (command_id, status, now()))
        self.db.commit()

    def on_mqtt_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            client.subscribe(self.topic_command, qos=1)
            self.publish_state()

    def on_mqtt_message(self, client, userdata, message):
        try:
            obj = json.loads(message.payload.decode("utf-8"))
            command_id = str(obj["command_id"])
            job_id = str(obj.get("job_id", ""))
            action = str(obj["action"])
            params = obj.get("parameters") or {}
            prior = self.db.execute("SELECT status FROM commands WHERE command_id=?", (command_id,)).fetchone()
            if prior:
                self.publish(self.topic_ack, {"command_id": command_id, "job_id": job_id, "status": "duplicate_ignored", "previous_status": prior[0]})
                return
            self.ack(command_id, job_id, "received")
            wire = self.translate(action, params)
            self.ack(command_id, job_id, "validated", "freenove_command", wire)
            self.robot.send(wire)
            self.ack(command_id, job_id, "sent", "completion_semantics", "server_queue_only")
        except Exception as exc:
            cid = locals().get("command_id", "unknown")
            jid = locals().get("job_id", "")
            self.ack(cid, jid, "rejected", reason=str(exc))

    def translate(self, action, p):
        if action == "motor_enable": return "S8 E0"
        if action == "motor_relax": return "S8 E1"
        if action == "sensor_home": return "S10 F1"
        if action == "move_xyz":
            vals = {k: float(p[k]) for k in ("x", "y", "z")}
            for axis, value in vals.items():
                low, high = self.bounds[axis]
                if not low <= value <= high:
                    raise ValueError(f"{axis}={value} outside configured range [{low},{high}]")
            return format_move(vals["x"], vals["y"], vals["z"])
        if action == "set_servo":
            index, angle = int(p["index"]), int(p["angle"])
            if index not in range(5): raise ValueError("servo index must be 0..4")
            if not 0 <= angle <= 180: raise ValueError("servo angle must be 0..180")
            return format_servo(index, angle)
        if action == "emergency_stop":
            if not self.allow_s13: raise ValueError("S13 is disabled; it terminates the Freenove server")
            return "S13 N1"
        raise ValueError(f"unsupported action: {action}")

    def on_robot_line(self, line):
        self.last_line = line
        match = re.fullmatch(r"S12\s+K(-?\d+)", line)
        if match:
            self.queue_count = int(match.group(1))
        self.publish_state()

    def on_robot_state(self, connected, error=None):
        self.last_error = error
        self.publish_state()

    def publish_state(self):
        self.publish(self.topic_state, {
            "connected": self.robot.connected,
            "server": f"{self.robot_host}:{self.robot_port}",
            "queue_count": self.queue_count,
            "last_server_message": self.last_line,
            "last_error": self.last_error,
            "home_position": {"x": 0.0, "y": 200.0, "z": 45.0},
        }, retain=True)

    def run(self):
        self.mqtt.connect(self.mqtt_host, self.mqtt_port, keepalive=30)
        self.mqtt.loop_start()
        self.robot.start()
        while not self.stop_event.wait(5):
            self.publish_state()
        self.robot.stop()
        self.mqtt.loop_stop()
        self.mqtt.disconnect()


if __name__ == "__main__":
    adapter = Adapter()
    signal.signal(signal.SIGTERM, lambda *_: adapter.stop_event.set())
    signal.signal(signal.SIGINT, lambda *_: adapter.stop_event.set())
    adapter.run()

