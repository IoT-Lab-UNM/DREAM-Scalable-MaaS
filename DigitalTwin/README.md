# README.md

# DHT22 Customized Mapper for KubeEdge v1.23

This repository contains a working customized KubeEdge mapper for two DHT22 sensors connected to a Raspberry Pi gateway (`pigateway`). The mapper reads temperature and humidity from two GPIO pins and reports the values to KubeEdge as digital twin updates in the `DeviceStatus` CRD.

## Overview

This setup is verified to work with:

* **KubeEdge v1.23**
* **Customized mapper**
* **Two DHT22 sensors**
* **GPIO4** for `dht22-sensor1`
* **GPIO17** for `dht22-sensor2`

The mapper successfully:

* registers to EdgeCore through DMI
* loads 2 devices and 2 device models
* starts the runtime polling loop
* reads both sensors every 3 seconds
* updates `DeviceStatus.status.twins.reported.value`
* updates the local EdgeCore SQLite twin database

## Repository Structure

```text
 dht22/
 ├── cmd/
 ├── data/
 ├── device/
 ├── driver/
 ├── resource/
 ├── config.yaml
 ├── go.mod
 ├── go.sum
 ├── Makefile
 ├── read_dht22_once.py
 ├── dht22_mapper
 ├── Dockerfile_nostream
 └── Dockerfile_stream
```

## Device Model

Create `dht22-devicemodel.yaml`:

```yaml
apiVersion: devices.kubeedge.io/v1beta1
kind: DeviceModel
metadata:
  name: dht22-model
  namespace: default
spec:
  properties:
    - name: temperature
      description: DHT22 temperature
      type: STRING
      accessMode: ReadOnly
      unit: Celsius
    - name: humidity
      description: DHT22 humidity
      type: STRING
      accessMode: ReadOnly
      unit: Percent
```

## Device Instances

Create `dht22-devices.yaml`:

```yaml
apiVersion: devices.kubeedge.io/v1beta1
kind: Device
metadata:
  name: dht22-sensor1
  namespace: default
spec:
  deviceModelRef:
    name: dht22-model
  nodeName: pigateway
  protocol:
    protocolName: customized
    configData: {}
  properties:
    - name: temperature
      collectCycle: 3000
      reportCycle: 3000
      reportToCloud: true
      visitors:
        protocolName: customized
        configData:
          dataType: string
          metric: temperature
          pin: GPIO4
    - name: humidity
      collectCycle: 3000
      reportCycle: 3000
      reportToCloud: true
      visitors:
        protocolName: customized
        configData:
          dataType: string
          metric: humidity
          pin: GPIO4
---
apiVersion: devices.kubeedge.io/v1beta1
kind: Device
metadata:
  name: dht22-sensor2
  namespace: default
spec:
  deviceModelRef:
    name: dht22-model
  nodeName: pigateway
  protocol:
    protocolName: customized
    configData: {}
  properties:
    - name: temperature
      collectCycle: 3000
      reportCycle: 3000
      reportToCloud: true
      visitors:
        protocolName: customized
        configData:
          dataType: string
          metric: temperature
          pin: GPIO17
    - name: humidity
      collectCycle: 3000
      reportCycle: 3000
      reportToCloud: true
      visitors:
        protocolName: customized
        configData:
          dataType: string
          metric: humidity
          pin: GPIO17
```

## Important Note About Time Units

A major issue during debugging was caused by wrong cycle units.

Wrong:

```yaml
collectCycle: 3000000000
reportCycle: 3000000000
```

This was interpreted as milliseconds and became about 34.7 days.

Correct:

```yaml
collectCycle: 3000
reportCycle: 3000
```

This means 3 seconds.

## Python Sensor Reader

Create `read_dht22_once.py`:

```python
#!/usr/bin/env python3
import sys
import json
import time
import board
import adafruit_dht

PIN_MAP = {
    "GPIO4": board.D4,
    "GPIO17": board.D17,
}

def read_sensor_once(pin_name: str):
    dht = adafruit_dht.DHT22(PIN_MAP[pin_name], use_pulseio=False)
    try:
        temperature = dht.temperature
        humidity = dht.humidity
        if temperature is None or humidity is None:
            raise RuntimeError("failed to read sensor")
        return {
            "temperature": round(temperature, 1),
            "humidity": round(humidity, 1),
        }
    finally:
        try:
            dht.exit()
        except Exception:
            pass

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: read_dht22_once.py <GPIO4|GPIO17>")

    pin_name = sys.argv[1].strip()
    if pin_name not in PIN_MAP:
        raise SystemExit(f"unsupported pin: {pin_name}")

    last_err = None

    for _ in range(5):
        try:
            result = read_sensor_once(pin_name)
            print(json.dumps(result))
            return
        except Exception as e:
            last_err = e
            time.sleep(2)

    raise SystemExit(f"sensor read failed after retries: {last_err}")

if __name__ == "__main__":
    main()
```

## Python Dependency Fix

Since the mapper is launched using `sudo`, the root Python environment also needs the required packages.

Install them with:

```bash
sudo python3 -m pip install adafruit-blinka adafruit-circuitpython-dht
```

Verify both normal user and root can read the sensor:

```bash
python3 ~/dht22/read_dht22_once.py GPIO4
python3 ~/dht22/read_dht22_once.py GPIO17
sudo python3 ~/dht22/read_dht22_once.py GPIO4
sudo python3 ~/dht22/read_dht22_once.py GPIO17
```

All four commands should return valid JSON.

## Build the Mapper

On the Pi:

```bash
cd ~/dht22
go build -o dht22_mapper ./cmd
```

## Apply the Device Model and Devices

On the Kubernetes control-plane node:

```bash
kubectl apply -f dht22-devicemodel.yaml
kubectl delete device dht22-sensor1 -n default --ignore-not-found
kubectl delete device dht22-sensor2 -n default --ignore-not-found
kubectl apply -f dht22-devices.yaml
```

## Run the Mapper

On the Pi:

```bash
cd ~/dht22
sudo rm -f /etc/kubeedge/dht22.sock
sudo ./dht22_mapper 2>&1 | tee mapper.log
```

## Verify DeviceStatus in Kubernetes

Check reported twin values from the master node:

```bash
kubectl get devicestatuses.devices.kubeedge.io dht22-sensor1 -n default -o yaml
kubectl get devicestatuses.devices.kubeedge.io dht22-sensor2 -n default -o yaml
```

Expected structure:

```yaml
status:
  twins:
    - propertyName: temperature
      reported:
        value: "23.4"
    - propertyName: humidity
      reported:
        value: "30.8"
```

## Verify Local Twin State in EdgeCore SQLite

On the Pi:

```bash
sqlite3 -header -column /var/lib/kubeedge/edgecore.db \
"SELECT deviceid, name, expected, actual, expected_meta, actual_meta FROM device_twin;"
```

Field meanings:

* `expected` = desired value
* `actual` = current reported sensor value
* `expected_meta` = metadata for desired state
* `actual_meta` = metadata for actual reported state

For this DHT22 sensing setup, the important live reading is mainly:

* `actual` in SQLite
* `status.twins[].reported.value` in `DeviceStatus`

## Example Working Result

The mapper reports:

* `dht22-sensor1`

  * temperature
  * humidity
* `dht22-sensor2`

  * temperature
  * humidity

with values visible in both:

* local EdgeCore SQLite twin DB
* Kubernetes `DeviceStatus` CRD

## Useful Commands

Watch debug logs:

```bash
grep -n "DEBUG" ~/dht22/mapper.log
```

Check successful reads:

```bash
grep -n "returning temperature\|returning humidity\|after GetDeviceData" ~/dht22/mapper.log
```

Check device statuses:

```bash
kubectl get devicestatuses.devices.kubeedge.io -A
```

Check local twin DB:

```bash
sqlite3 -header -column /var/lib/kubeedge/edgecore.db \
"SELECT deviceid, name, expected, actual, expected_meta, actual_meta FROM device_twin;"
```

## Troubleshooting

If the mapper registers but does not report values, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

## Example Git Commit

```bash
git add .
git commit -m "Fix DHT22 customized mapper runtime polling and DeviceStatus reporting"
git push
```

---

# TROUBLESHOOTING.md

# Troubleshooting DHT22 Customized Mapper on KubeEdge v1.23

This document captures the main issues encountered while making the customized DHT22 mapper work with KubeEdge v1.23, and how each issue was resolved.

## 1. Mapper Registered but Did Not Report Sensor Values

### Symptom

The mapper started successfully and registered to EdgeCore, but no sensor values appeared in:

* `DeviceStatus.status`
* local `device_twin` DB rows
* mapper debug output for runtime polling

Typical startup log:

```text
Mapper will register to edgecore
RegisterMapper returned deviceList=2 deviceModelList=2
Mapper register finished
devInit finished
uds socket path: /etc/kubeedge/dht22.sock
```

But nothing after that.

### Cause

The mapper loaded devices during `DevInit()`, but the runtime device-start path was not being triggered for freshly loaded devices.

### Fix

Ensure the device start routine is launched during `DevInit()` after each device instance is loaded:

```go
cur := new(driver.CustomizedDev)
cur.Instance = *instance
d.devices[instance.ID] = cur

ctx, cancelFunc := context.WithCancel(context.Background())
d.deviceMuxs[instance.ID] = cancelFunc
d.wg.Add(1)
go d.start(ctx, d.devices[instance.ID])
```

---

## 2. Wrong `collectCycle` / `reportCycle` Units

### Symptom

The runtime path started, but polling still did not seem to happen.

Debug logs showed:

```text
collect=833h20m0s
```

### Cause

The YAML used:

```yaml
collectCycle: 3000000000
reportCycle: 3000000000
```

The code interpreted these values as milliseconds:

```go
time.Millisecond * time.Duration(twin.Property.CollectCycle)
```

So `3000000000` became about 34.7 days.

### Fix

Use 3-second intervals:

```yaml
collectCycle: 3000
reportCycle: 3000
```

---

## 3. `DeviceStatus` Stayed Empty

### Symptom

Even after device registration, these commands showed:

```bash
kubectl get devicestatuses.devices.kubeedge.io dht22-sensor1 -n default -o yaml
kubectl get devicestatuses.devices.kubeedge.io dht22-sensor2 -n default -o yaml
```

with:

```yaml
status: {}
```

### Causes

There were multiple contributing issues:

* runtime start path not triggered
* polling interval set to ~34 days
* Python sensor execution failing under `sudo`

### Fix

Fix all three issues. After that, `DeviceStatus.status.twins` began updating correctly.

---

## 4. Python Reader Worked as Normal User but Failed Under `sudo`

### Symptom

Direct Python tests worked:

```bash
python3 ~/dht22/read_dht22_once.py GPIO4
python3 ~/dht22/read_dht22_once.py GPIO17
```

But root failed:

```bash
sudo python3 ~/dht22/read_dht22_once.py GPIO4
sudo python3 ~/dht22/read_dht22_once.py GPIO17
```

with:

```text
ModuleNotFoundError: No module named 'board'
```

The mapper log showed:

```text
failed to execute sensor reader: exit status 1
```

### Cause

The mapper was launched using `sudo`, so the Go process executed Python in the root environment. Root did not have the required Python libraries.

### Fix

Install required packages for root too:

```bash
sudo python3 -m pip install adafruit-blinka adafruit-circuitpython-dht
```

Then verify root Python works:

```bash
sudo python3 ~/dht22/read_dht22_once.py GPIO4
sudo python3 ~/dht22/read_dht22_once.py GPIO17
```

---

## 5. Confirming the Real Runtime Path

### Observation

Some debug lines were added in helper functions, but they never appeared in logs. That initially made it look like the code path was not running.

### Cause

The debug lines were added in a helper path that was not the actual periodic collection path.

### Correct Runtime Path

The real runtime path was through:

* `start()`
* `dataHandler()`
* `TwinData.Run()`
* `GetDeviceData()`

Debugging this path revealed the actual issue.

---

## 6. `reportToCloud` and Device-Level Status Flag

### Observation

Logs showed:

```text
statusReport=false
```

while property-level logs showed:

```text
reportToCloud=true
```

### Interpretation

For this setup, the important reporting path was the property/twin-level reporting:

* `twin.Property.ReportToCloud = true`

That was sufficient to successfully update `DeviceStatus.status.twins`.

So the device-level status report flag being false did not block the working sensor-twin updates.

---

## 7. Meaning of `expected` and `actual` in Local SQLite Twin DB

Query used:

```bash
sqlite3 -header -column /var/lib/kubeedge/edgecore.db \
"SELECT deviceid, name, expected, actual, expected_meta, actual_meta FROM device_twin;"
```

### Meaning

* `expected` = desired twin value
* `actual` = actual reported sensor value
* `expected_meta` = metadata for desired value
* `actual_meta` = metadata for actual reported value

### For This DHT22 Setup

Since DHT22 is a read-only sensing device:

* the important live twin reading is mainly `actual`
* the cloud-visible equivalent is `DeviceStatus.status.twins[].reported.value`

---

## 8. Verifying a Healthy Working System

### Mapper Log

A healthy runtime log should include:

```text
DEBUG start entered: ...
DEBUG dataHandler entered: ...
DEBUG launching TwinData.Run: ... collect=3s reportToCloud=true
DEBUG GetDeviceData called: pin=GPIO4 metric=temperature
DEBUG python output raw: {"temperature": 23.4, "humidity": 30.8}
DEBUG returning temperature=23.4
DEBUG after GetDeviceData: results=23.4 err=<nil>
```

### DeviceStatus

Example:

```yaml
status:
  twins:
    - propertyName: temperature
      reported:
        value: "23.4"
    - propertyName: humidity
      reported:
        value: "30.8"
```

### Local SQLite Twin DB

Example:

```text
deviceid               name         expected   actual
default/dht22-sensor1  temperature             23.4
default/dht22-sensor1  humidity                30.8
default/dht22-sensor2  temperature             23.6
default/dht22-sensor2  humidity                33.8
```

---

## 9. Most Useful Debug Commands

### Check mapper runtime logs

```bash
grep -n "DEBUG" ~/dht22/mapper.log
```

### Check successful sensor reads

```bash
grep -n "returning temperature\|returning humidity\|after GetDeviceData" ~/dht22/mapper.log
```

### Check live `DeviceStatus`

```bash
kubectl get devicestatuses.devices.kubeedge.io dht22-sensor1 -n default -o yaml
kubectl get devicestatuses.devices.kubeedge.io dht22-sensor2 -n default -o yaml
```

### Check local twin DB

```bash
sqlite3 -header -column /var/lib/kubeedge/edgecore.db \
"SELECT deviceid, name, expected, actual, expected_meta, actual_meta FROM device_twin;"
```

### Test Python reader directly

```bash
python3 ~/dht22/read_dht22_once.py GPIO4
python3 ~/dht22/read_dht22_once.py GPIO17
sudo python3 ~/dht22/read_dht22_once.py GPIO4
sudo python3 ~/dht22/read_dht22_once.py GPIO17
```

---

## 10. Final Root Causes Summary

The final working setup required fixing all of these:

1. device runtime start path after initialization
2. wrong cycle time units
3. missing Python libraries in root environment
4. debugging the actual runtime path rather than a helper path

Once these were resolved, the mapper successfully updated both:

* `DeviceStatus.status.twins`
* local EdgeCore `device_twin` SQLite table

---

## 11. Suggested Cleanup After Success

After confirming the system works:

* keep a copy of the final working files
* remove noisy temporary debug logs if desired
* commit the working version to GitHub
