from octorest import OctoRest
import os
import time

client = OctoRest(
    url="http://10.88.202.187:5000",
    apikey="GU19lQsUwEnXSTGxoOSAKjfw925uTQDUncjYfkKKDxU"
)

print(client.version)
print(client.printer())

gcode_path = "/home/henok/DREAM_1.3-scalable-DIAM-MaaS/Ender3_Printer/f4u2.gcode"
gcode_name = os.path.basename(gcode_path)

if not os.path.exists(gcode_path):
    raise FileNotFoundError(f"G-code file not found: {gcode_path}")

print(f"Uploading {gcode_name}...")
client.upload(gcode_path)

time.sleep(2)

print(f"Selecting {gcode_name} and starting print...")
client.select(gcode_name, print=True)

print("Task started")

# temps = client.tool()
# print(temps)