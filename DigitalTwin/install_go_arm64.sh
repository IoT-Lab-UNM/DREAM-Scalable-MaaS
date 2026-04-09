#!/usr/bin/env bash
set -euo pipefail

cd ~

GO_TAR="go1.24.2.linux-arm64.tar.gz"
GO_URL="https://go.dev/dl/${GO_TAR}"

echo "=== Downloading Go ==="
wget -O "$GO_TAR" "$GO_URL"

echo "=== Removing old Go (if any) ==="
sudo rm -rf /usr/local/go

echo "=== Extracting Go ==="
sudo tar -C /usr/local -xzf "$GO_TAR"

echo "=== Adding Go to PATH in ~/.profile ==="
if ! grep -q '/usr/local/go/bin' ~/.profile; then
    echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.profile
fi

export PATH=$PATH:/usr/local/go/bin

echo "=== Verifying Go installation ==="
go version

echo "=== Done ==="
echo "For future new terminals, run:"
echo "  source ~/.profile"