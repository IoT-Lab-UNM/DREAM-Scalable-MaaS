#!/usr/bin/env bash
set -euo pipefail

cd ~/dht22

echo "===== cmd/main.go ====="
sed -n '1,220p' cmd/main.go

echo
echo "===== driver/devicetype.go ====="
sed -n '1,220p' driver/devicetype.go

echo
echo "===== driver/driver.go ====="
sed -n '1,220p' driver/driver.go

echo
echo "===== device/devicestatus.go ====="
sed -n '1,220p' device/devicestatus.go

echo
echo "===== device/devicetwin.go ====="
sed -n '1,220p' device/devicetwin.go

echo
echo "===== More lines if needed ====="
sed -n '221,440p' cmd/main.go
sed -n '221,440p' driver/devicetype.go
sed -n '221,440p' driver/driver.go
sed -n '221,440p' device/devicestatus.go
sed -n '221,440p' device/devicetwin.go