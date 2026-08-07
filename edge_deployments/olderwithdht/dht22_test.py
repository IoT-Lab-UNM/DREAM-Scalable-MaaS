#!/usr/bin/env python3
import time
import board
import adafruit_dht

# Sensor 1 on GPIO4
dht1 = adafruit_dht.DHT22(board.D4)

# Sensor 2 on GPIO17
dht2 = adafruit_dht.DHT22(board.D17)

while True:
    try:
        temp1 = dht1.temperature
        hum1 = dht1.humidity

        if temp1 is not None and hum1 is not None:
            print(f"Sensor 1 -> Temperature: {temp1:.1f} C | Humidity: {hum1:.1f}%")
        else:
            print("Sensor 1 -> Failed to get reading")

    except Exception as e:
        print(f"Sensor 1 -> Read error: {e}")

    try:
        temp2 = dht2.temperature
        hum2 = dht2.humidity

        if temp2 is not None and hum2 is not None:
            print(f"Sensor 2 -> Temperature: {temp2:.1f} C | Humidity: {hum2:.1f}%")
        else:
            print("Sensor 2 -> Failed to get reading")

    except Exception as e:
        print(f"Sensor 2 -> Read error: {e}")

    print("-" * 60)
    time.sleep(3)

################################################
# For single sensor

# #!/usr/bin/env python3
# import time
# import board
# import adafruit_dht

# dht = adafruit_dht.DHT22(board.D4)

# while True:
#     try:
#         temperature_c = dht.temperature
#         humidity = dht.humidity
#         print(f"Temperature: {temperature_c:.1f} C | Humidity: {humidity:.1f}%")
#     except Exception as e:
#         print(f"Read error: {e}")
#     time.sleep(3)
####################################################