import json
import os
import requests
from paho.mqtt import client as mqtt

MQTT_HOST = "10.250.0.1"
TOPIC = "print/jobs"
MINIO_BASE = "http://10.250.0.1:9000"
DOWNLOAD_DIR = "/tmp/print_jobs"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def send_to_printer(filepath: str) -> None:
    print(f"[PRINT] Processing file: {filepath}")

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode("utf-8"))

    if payload.get("target_site") != "EDGE1":
        return

    job_id = payload["job_id"]
    obj = payload["object"]
    url = f"{MINIO_BASE}/{obj}"
    out = os.path.join(DOWNLOAD_DIR, f"{job_id}-{os.path.basename(obj)}")

    print(f"[DEBUG] Downloading: {url}")
    r = requests.get(url, timeout=30)
    print(f"[DEBUG] HTTP status: {r.status_code}")
    print(f"[DEBUG] Response headers: {dict(r.headers)}")

    r.raise_for_status()

    with open(out, "wb") as f:
        f.write(r.content)

    send_to_printer(out)

client = mqtt.Client()
client.on_message = on_message
client.connect(MQTT_HOST, 1883, 60)
client.subscribe(TOPIC)
print("Listening for jobs...")
client.loop_forever()
