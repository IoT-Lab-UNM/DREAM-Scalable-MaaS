#!/usr/bin/env python3
import sys
import json
import board
import adafruit_dht

PIN_MAP = {
    "GPIO4": board.D4,
    "GPIO17": board.D17,
}

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: read_dht22_once.py <GPIO4|GPIO17>")

    pin_name = sys.argv[1].strip()
    if pin_name not in PIN_MAP:
        raise SystemExit(f"unsupported pin: {pin_name}")

    dht = adafruit_dht.DHT22(PIN_MAP[pin_name])

    try:
        temperature = dht.temperature
        humidity = dht.humidity

        if temperature is None or humidity is None:
            raise RuntimeError("failed to read sensor")

        print(json.dumps({
            "temperature": round(temperature, 1),
            "humidity": round(humidity, 1)
        }))
    finally:
        try:
            dht.exit()
        except Exception:
            pass

if __name__ == "__main__":
    main()