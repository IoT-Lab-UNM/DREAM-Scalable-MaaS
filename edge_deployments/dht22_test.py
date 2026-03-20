#!/usr/bin/env python3
import sys
import time

try:
    import board
    import adafruit_dht
except ImportError as exc:
    print(f"Import error: {exc}")
    print("Activate the virtual environment first, or run setup_dht22.sh.")
    sys.exit(1)

GPIO_PIN = board.D4
READ_INTERVAL_SECONDS = 3

dht = adafruit_dht.DHT22(GPIO_PIN)

print("Starting DHT22 sensor test on Raspberry Pi...")
print("Expected wiring:")
print("  DHT22 VCC  -> Pi 3.3V")
print("  DHT22 DATA -> Pi GPIO4 (physical pin 7)")
print("  DHT22 GND  -> Pi GND")
print("Press Ctrl+C to stop.\n")

try:
    while True:
        try:
            temperature_c = dht.temperature
            humidity = dht.humidity

            if temperature_c is None or humidity is None:
                print("Sensor read returned no data. Check wiring and try again.")
            else:
                print(
                    f"Temperature: {temperature_c:.1f} C | "
                    f"Humidity: {humidity:.1f}%"
                )

        except RuntimeError as exc:
            # DHT sensors often throw transient read errors; retrying is normal.
            print(f"Transient read error: {exc}")

        except Exception as exc:
            print(f"Unexpected error: {exc}")

        time.sleep(READ_INTERVAL_SECONDS)

except KeyboardInterrupt:
    print("\nStopping DHT22 test...")

finally:
    dht.exit()



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