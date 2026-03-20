#!/usr/bin/env python3
# Another alternative for test reading

import time
import board
import adafruit_dht

dht = adafruit_dht.DHT22(board.D4)

while True:
    try:
        temperature_c = dht.temperature
        humidity = dht.humidity

        if temperature_c is not None and humidity is not None:
            print(f"Temperature: {temperature_c:.1f} C | Humidity: {humidity:.1f}%")
        else:
            print("Sensor returned incomplete data")
    except Exception as e:
        print(f"Read error: {e}")
    time.sleep(3)