from octorest import OctoRest
import time

client = OctoRest(
    url="http://10.88.202.187:5000",
    apikey = "GU19lQsUwEnXSTGxoOSAKjfw925uTQDUncjYfkKKDxU"
)

print(client.version)
print(client.printer)

#client.upload("f4u2.gcode")
#client.select("f4u2.gcode",print=True)
print("Task started")

temps = client.tool()
print(temps)