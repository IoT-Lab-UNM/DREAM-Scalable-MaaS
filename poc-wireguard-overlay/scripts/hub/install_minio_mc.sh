#!/bin/bash
set -e
curl -fsSL https://dl.min.io/client/mc/release/linux-amd64/mc -o ~/mc
chmod +x ~/mc
sudo mv ~/mc /usr/local/bin/mc
mc --version
