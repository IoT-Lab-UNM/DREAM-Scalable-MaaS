# OctoPrint Docker Setup and Python API Tutorial

This README explains how to run OctoPrint in a Docker container on a Raspberry Pi, connect it to a 3D printer, create an OctoPrint API key, and control print jobs using Python through the `octorest` library.

> **Security note:** Do not commit Raspberry Pi login credentials, OctoPrint usernames/passwords, or API keys to a public GitHub repository. Store secrets in a private password manager or in a local `.env` file that is excluded from Git.

---

## Table of Contents

- [System Overview](#system-overview)
- [Prerequisites](#prerequisites)
- [Raspberry Pi and OctoPrint Notes](#raspberry-pi-and-octoprint-notes)
- [1. Start the OctoPrint Docker Container](#1-start-the-octoprint-docker-container)
- [2. Create an OctoPrint API Key](#2-create-an-octoprint-api-key)
- [3. Create a Python Environment](#3-create-a-python-environment)
- [4. Verify the Raspberry Pi and Printer Connection](#4-verify-the-raspberry-pi-and-printer-connection)
- [5. Connect to OctoPrint from Python](#5-connect-to-octoprint-from-python)
- [6. Upload G-code and Start a Print](#6-upload-g-code-and-start-a-print)
- [7. Full Test Script](#7-full-test-script)
- [Useful Commands](#useful-commands)
- [TODO](#todo)
- [Reference](#reference)

---

## System Overview

The setup uses:

- A Raspberry Pi running Ubuntu
- Docker
- OctoPrint running as a Docker container
- A 3D printer connected to the Raspberry Pi through `/dev/ttyUSB0`
- Python 3.10
- The [`octorest`](https://pypi.org/project/octorest/) Python library for interacting with the OctoPrint REST API

The OctoPrint web interface is exposed on port `5000`.

Example OctoPrint URL:

```text
http://<RASPBERRY_PI_IP>:5000
```

---

## Prerequisites

Make sure the Raspberry Pi has the following installed:

- Ubuntu
- Docker
- Python 3.10
- `pip3` or Conda
- Network connectivity between your development machine and the Raspberry Pi
- A 3D printer connected to the Raspberry Pi, usually through `/dev/ttyUSB0`

---

## Raspberry Pi and OctoPrint Notes

The Raspberry Pi is configured to stop existing Docker containers on restart and initialize a fresh OctoPrint container.

Relevant files on the Raspberry Pi:

```text
~/scripts/start_octoprint.sh
/etc/systemd/system/octoprint-autostart.services
```

> **Note:** The tutorial source indicates that all Docker containers may be stopped during Raspberry Pi startup. Be careful if the Raspberry Pi is also running other Docker-based services.

---

## 1. Start the OctoPrint Docker Container

Run the following command on the Raspberry Pi:

```bash
docker run -d \
  --name octoprint \
  -p 5000:5000 \
  --device=/dev/ttyUSB0 \
  -v octoprint:/octoprint \
  octoprint/octoprint
```

This command:

- Runs OctoPrint in detached mode
- Names the container `octoprint`
- Maps host port `5000` to container port `5000`
- Passes the 3D printer USB device into the container
- Stores OctoPrint data in a Docker volume named `octoprint`

### Optional Alias

The Raspberry Pi may already have an alias named `dockerprint` for starting the OctoPrint container.

You can check whether the alias exists using:

```bash
alias dockerprint
```

If needed, you can create the alias manually:

```bash
alias dockerprint='docker run -d --name octoprint -p 5000:5000 --device=/dev/ttyUSB0 -v octoprint:/octoprint octoprint/octoprint'
```

To make the alias persistent, add it to `~/.bashrc`:

```bash
echo "alias dockerprint='docker run -d --name octoprint -p 5000:5000 --device=/dev/ttyUSB0 -v octoprint:/octoprint octoprint/octoprint'" >> ~/.bashrc
source ~/.bashrc
```

---

## 2. Create an OctoPrint API Key

Open the OctoPrint web interface in a browser:

```text
http://<RASPBERRY_PI_IP>:5000
```

Then go to:

```text
Settings > Application Keys
```

Create a new application key for your Python client.

Recommended key label:

```text
testing
```

Do **not** hard-code the API key in scripts that will be committed to GitHub. Use an environment variable instead.

Example:

```bash
export OCTOPRINT_URL="http://<RASPBERRY_PI_IP>:5000"
export OCTOPRINT_API_KEY="your_api_key_here"
```

---

## 3. Create a Python Environment

Create a Python environment using Conda or `venv`.

### Option A: Conda

```bash
conda create -n octoprint-api python=3.10 -y
conda activate octoprint-api
pip install octorest
```

### Option B: Python `venv`

```bash
python3.10 -m venv octoprint-api-env
source octoprint-api-env/bin/activate
pip install --upgrade pip
pip install octorest
```

---

## 4. Verify the Raspberry Pi and Printer Connection

The current OctoPrint settings should initialize the Raspberry Pi-to-printer connection automatically.

You can verify the container is running using:

```bash
docker ps
```

You can also check the OctoPrint container logs using:

```bash
docker logs -f octoprint
```

If the printer is not detected, confirm that the USB device exists:

```bash
ls -l /dev/ttyUSB0
```

If the device path is different, update the Docker command accordingly.

---

## 5. Connect to OctoPrint from Python

Create a Python file named `connect_octoprint.py`:

```python
import os
from octorest import OctoRest

OCTOPRINT_URL = os.getenv("OCTOPRINT_URL", "http://<RASPBERRY_PI_IP>:5000")
OCTOPRINT_API_KEY = os.getenv("OCTOPRINT_API_KEY", "your_api_key_here")

client = OctoRest(
    url=OCTOPRINT_URL,
    apikey=OCTOPRINT_API_KEY,
)

print(client.version)
print(client.printer)
```

Run it:

```bash
python connect_octoprint.py
```

Expected output should include OctoPrint version information and printer status.

---

## 6. Upload G-code and Start a Print

After verifying the connection, you can upload a G-code file and start printing.

Example:

```python
client.upload("test.gcode")
client.select("test.gcode", print=True)
print("Task started")
```

Make sure the G-code file exists in the same directory as the Python script, or provide the full path to the file.

---

## 7. Full Test Script

Create a file named `print_test.py`:

```python
import os
import time
from octorest import OctoRest

OCTOPRINT_URL = os.getenv("OCTOPRINT_URL", "http://<RASPBERRY_PI_IP>:5000")
OCTOPRINT_API_KEY = os.getenv("OCTOPRINT_API_KEY", "your_api_key_here")
GCODE_FILE = "f4u2.gcode"

client = OctoRest(
    url=OCTOPRINT_URL,
    apikey=OCTOPRINT_API_KEY,
)

print("OctoPrint version:")
print(client.version)

print("Printer status:")
print(client.printer)

print(f"Uploading {GCODE_FILE}...")
client.upload(GCODE_FILE)

print(f"Starting print job for {GCODE_FILE}...")
client.select(GCODE_FILE, print=True)

print("Task started")
```

Before running the script, export your OctoPrint configuration:

```bash
export OCTOPRINT_URL="http://<RASPBERRY_PI_IP>:5000"
export OCTOPRINT_API_KEY="your_api_key_here"
```

Run the script:

```bash
python print_test.py
```

---

## Useful Commands

### Check Running Containers

```bash
docker ps
```

### Stop the OctoPrint Container

```bash
docker stop octoprint
```

### Remove the OctoPrint Container

```bash
docker rm octoprint
```

### Restart OctoPrint Manually

```bash
docker stop octoprint || true
docker rm octoprint || true

docker run -d \
  --name octoprint \
  -p 5000:5000 \
  --device=/dev/ttyUSB0 \
  -v octoprint:/octoprint \
  octoprint/octoprint
```

### Check the Autostart Service

```bash
systemctl status octoprint-autostart.services
```

### Restart the Autostart Service

```bash
sudo systemctl restart octoprint-autostart.services
```

---

## TODO

- Improve the Raspberry Pi startup script so that it safely stops only the previous OctoPrint container instead of killing all Docker containers.
- Confirm whether the OctoPrint USB device path is always `/dev/ttyUSB0` or whether a persistent device rule should be created.
- Move API keys and credentials into environment variables or a local `.env` file.
- Add error handling to the Python scripts for printer offline, missing G-code file, and failed upload cases.

---

## Reference

- [`octorest` Python API package](https://pypi.org/project/octorest/)
- [OctoPrint Docker image](https://hub.docker.com/r/octoprint/octoprint)
