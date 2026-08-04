#!/bin/bash
set -e

CONTAINER_NAME="octoprint"

echo "Removing the previous OctoPrint container, if present..."

if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
    docker rm -f "$CONTAINER_NAME"
fi

echo "Starting OctoPrint..."

docker run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  -p 5000:5000 \
  -v octoprint:/octoprint \
  --device=/dev/ttyUSB0:/dev/ttyUSB0 \
  octoprint/octoprint

echo "OctoPrint started."
# chmod +x /home/secnet/scripts/start_octoprint.sh