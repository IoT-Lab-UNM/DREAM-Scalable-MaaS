#!/usr/bin/env python3
import json
import time
from datetime import datetime, timezone

import board
import adafruit_dht
import paho.mqtt.client as mqtt

BROKER = "127.0.0.1"
PORT = 1883

TOPIC1 = "$hw/events/device/dht22-sensor1/twin/update"
TOPIC2 = "$hw/events/device/dht22-sensor2/twin/update"

dht1 = adafruit_dht.DHT22(board.D4)
dht2 = adafruit_dht.DHT22(board.D17)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="dht22-kubeedge-mapper")
client.connect(BROKER, PORT, 60)
client.loop_start()

def ts_iso():
    return datetime.now(timezone.utc).isoformat()

def twin_payload(temp, hum):
    now_unix = int(time.time())
    return {
        "event_id": str(now_unix),
        "timestamp": now_unix,
        "twin": {
            "temperature": {
                "actual": {
                    "value": f"{temp:.1f}",
                    "metadata": {"timestamp": ts_iso()}
                }
            },
            "humidity": {
                "actual": {
                    "value": f"{hum:.1f}",
                    "metadata": {"timestamp": ts_iso()}
                }
            }
        }
    }

while True:
    try:
        t1 = dht1.temperature
        h1 = dht1.humidity
        if t1 is not None and h1 is not None:
            client.publish(TOPIC1, json.dumps(twin_payload(t1, h1)), qos=1)
            print(f"sensor1 twin update: T={t1:.1f} H={h1:.1f}")
    except Exception as e:
        print(f"sensor1 error: {e}")

    try:
        t2 = dht2.temperature
        h2 = dht2.humidity
        if t2 is not None and h2 is not None:
            client.publish(TOPIC2, json.dumps(twin_payload(t2, h2)), qos=1)
            print(f"sensor2 twin update: T={t2:.1f} H={h2:.1f}")
    except Exception as e:
        print(f"sensor2 error: {e}")

    time.sleep(3)