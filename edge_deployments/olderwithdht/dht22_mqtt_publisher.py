#!/usr/bin/env python3
import time
import json
from datetime import datetime, timezone

import board
import adafruit_dht
import paho.mqtt.client as mqtt

# MQTT broker settings
MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883

# Separate MQTT topics
TOPIC_SENSOR1 = "factory/pigateway/dht22/sensor1"
TOPIC_SENSOR2 = "factory/pigateway/dht22/sensor2"

# DHT22 sensors
dht1 = adafruit_dht.DHT22(board.D4)
dht2 = adafruit_dht.DHT22(board.D17)

# MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="pigateway-dht22-publisher")
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def publish_reading(topic, sensor_name, gpio_name, temperature, humidity):
    payload = {
        "gateway": "pigateway",
        "sensor": sensor_name,
        "type": "DHT22",
        "gpio": gpio_name,
        "temperature_c": round(temperature, 1),
        "humidity_percent": round(humidity, 1),
        "timestamp": now_utc()
    }

    result = client.publish(topic, json.dumps(payload), qos=1)
    if result.rc == 0:
        print(f"Published to {topic}: {payload}")
    else:
        print(f"Failed to publish to {topic}, rc={result.rc}")


while True:
    try:
        temp1 = dht1.temperature
        hum1 = dht1.humidity

        if temp1 is not None and hum1 is not None:
            print(f"Sensor 1 -> Temperature: {temp1:.1f} C | Humidity: {hum1:.1f}%")
            publish_reading(TOPIC_SENSOR1, "sensor1", "GPIO4", temp1, hum1)
        else:
            print("Sensor 1 -> Failed to get reading")

    except Exception as e:
        print(f"Sensor 1 -> Read error: {e}")

    try:
        temp2 = dht2.temperature
        hum2 = dht2.humidity

        if temp2 is not None and hum2 is not None:
            print(f"Sensor 2 -> Temperature: {temp2:.1f} C | Humidity: {hum2:.1f}%")
            publish_reading(TOPIC_SENSOR2, "sensor2", "GPIO17", temp2, hum2)
        else:
            print("Sensor 2 -> Failed to get reading")

    except Exception as e:
        print(f"Sensor 2 -> Read error: {e}")

    print("-" * 60)
    time.sleep(3)