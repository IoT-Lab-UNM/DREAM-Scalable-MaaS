#!/usr/bin/env bash
set -Eeuo pipefail

# Prepare an ARM64 Raspberry Pi running Ubuntu/Debian
# for KubeEdge EdgeCore with containerd CRI.
#
# This script preserves Docker if already installed.
# It does NOT install a CNI on the edge node.

log()  { printf '\n[%s] %s\n' "$(date '+%F %T')" "$*"; }
warn() { printf '\nWARNING: %s\n' "$*" >&2; }
die()  { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

restore_containerd_config() {
  if [[ -n "${CONTAINERD_BACKUP:-}" && -f "${CONTAINERD_BACKUP}" ]]; then
    warn "Restoring the previous containerd configuration..."
    sudo cp -a "${CONTAINERD_BACKUP}" /etc/containerd/config.toml
    sudo systemctl restart containerd || true
    if systemctl list-unit-files --type=service 2>/dev/null | grep -q '^docker.service'; then
      sudo systemctl restart docker || true
    fi
  fi
}

trap 'warn "Setup failed at line $LINENO."; restore_containerd_config' ERR

log "========== Edge runtime preparation =========="

log "[1/9] Checking OS, hostname, architecture, and kernel..."
cat /etc/os-release
printf 'Hostname: %s\n' "$(hostname)"
uname -m
uname -r

require_cmd sudo
require_cmd systemctl
require_cmd apt-get
require_cmd python3

ARCH="$(uname -m)"
case "$ARCH" in
  aarch64|arm64) : ;;
  *) warn "This script was designed for an ARM64 Raspberry Pi; detected: $ARCH" ;;
esac

if [[ -r /etc/os-release ]]; then
  . /etc/os-release
  if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "22.04" ]]; then
    warn "Expected Ubuntu 22.04; detected ${PRETTY_NAME:-unknown}. Continuing cautiously."
  fi
fi

log "[2/9] Preserving Docker/OctoPrint and checking current services..."
if command -v docker >/dev/null 2>&1; then
  sudo systemctl is-active --quiet docker \
    || die "Docker is installed but docker.service is not active."

  docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'

  if docker ps -a --format '{{.Names}}' | grep -qx 'octoprint'; then
    echo "OctoPrint container found and will be preserved."
  else
    warn "No container named 'octoprint' was found. Nothing will be removed."
  fi
else
  warn "Docker is not installed. This script will not install or remove Docker."
fi

log "[3/9] Disabling swap persistently..."
sudo swapoff -a
FSTAB_BACKUP="/etc/fstab.backup.$(date +%Y%m%d-%H%M%S)"
sudo cp -a /etc/fstab "$FSTAB_BACKUP"
sudo sed -Ei '/^[[:space:]]*#/! { /[[:space:]]swap[[:space:]]/ s/^/#/ }' /etc/fstab
printf 'fstab backup: %s\n' "$FSTAB_BACKUP"

log "[4/9] Loading kernel modules..."
cat <<'MODULES' | sudo tee /etc/modules-load.d/kubeedge.conf >/dev/null
overlay
br_netfilter
MODULES
sudo modprobe overlay
sudo modprobe br_netfilter

log "[5/9] Applying sysctl settings..."
cat <<'SYSCTL' | sudo tee /etc/sysctl.d/99-kubeedge.conf >/dev/null
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
SYSCTL
sudo sysctl --system >/dev/null

lsmod | grep -E '(^|[[:space:]])(overlay|br_netfilter)([[:space:]]|$)' || true
sysctl net.bridge.bridge-nf-call-iptables
sysctl net.bridge.bridge-nf-call-ip6tables
sysctl net.ipv4.ip_forward

log "[6/9] Ensuring containerd is installed..."
if ! command -v containerd >/dev/null 2>&1; then
  warn "containerd is not installed. Detecting the host package environment and installing it automatically..."

  sudo apt-get update

  if dpkg-query -W -f='${Status}' docker-ce 2>/dev/null | grep -q 'install ok installed'; then
    log "Docker CE detected; installing matching containerd.io package family."
    sudo apt-get install -y containerd.io

  elif dpkg-query -W -f='${Status}' docker.io 2>/dev/null | grep -q 'install ok installed'; then
    log "Ubuntu docker.io detected; installing Ubuntu containerd package."
    sudo apt-get install -y containerd

  elif [[ "${ID:-}" == "ubuntu" && "${VERSION_ID:-}" == "22.04" ]]; then
    log "Fresh Ubuntu 22.04 node detected with no Docker/containerd."
    log "Installing containerd from the same Ubuntu repository configured on the node."
    sudo apt-get install -y containerd

  else
    die "containerd is absent and this OS/package environment is not supported automatically by this script."
  fi
fi

containerd --version
sudo systemctl enable --now containerd

log "[7/9] Backing up and preparing containerd CRI configuration..."
sudo mkdir -p /etc/containerd

if [[ -f /etc/containerd/config.toml ]]; then
  CONTAINERD_BACKUP="/etc/containerd/config.toml.backup.$(date +%Y%m%d-%H%M%S)"
  sudo cp -a /etc/containerd/config.toml "$CONTAINERD_BACKUP"
  printf 'containerd config backup: %s\n' "$CONTAINERD_BACKUP"
else
  sudo containerd config default | sudo tee /etc/containerd/config.toml >/dev/null
  CONTAINERD_BACKUP=""
fi

# Enable CRI if it is explicitly disabled and use systemd cgroups for runc.
sudo python3 - <<'PY'
from pathlib import Path
import re

path = Path('/etc/containerd/config.toml')
text = path.read_text()

pat = re.compile(r'(?m)^\s*disabled_plugins\s*=\s*\[(.*?)\]\s*$')
m = pat.search(text)
if m:
    raw = m.group(1)
    items = [x.strip() for x in raw.split(',') if x.strip()]
    items = [x for x in items if x.strip('"\'') != 'cri']
    repl = 'disabled_plugins = [' + ', '.join(items) + ']'
    text = text[:m.start()] + repl + text[m.end():]

text = re.sub(r'SystemdCgroup\s*=\s*false', 'SystemdCgroup = true', text)
path.write_text(text)
PY

log "[8/9] Restarting containerd and validating CRI..."
sudo systemctl daemon-reload
sudo systemctl restart containerd
sudo systemctl is-active --quiet containerd || die "containerd failed to start."

if ! sudo ctr plugins ls 2>/dev/null | awk 'tolower($0) ~ /cri/ && $NF == "ok" {found=1} END {exit !found}'; then
  sudo ctr plugins ls | grep -i cri || true
  die "containerd CRI plugin is not reporting status 'ok'."
fi

echo "containerd CRI plugin: OK"

# Docker may use a separate managed containerd, but verify Docker remains healthy.
if command -v docker >/dev/null 2>&1; then
  if systemctl list-unit-files --type=service 2>/dev/null | grep -q '^docker.service'; then
    sudo systemctl restart docker
    sudo systemctl is-active --quiet docker || die "Docker did not recover after runtime preparation."
  fi
  docker info >/dev/null
  docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
fi

log "[9/9] Final runtime checks..."
[[ -S /run/containerd/containerd.sock ]] \
  || die "CRI socket /run/containerd/containerd.sock was not found."

printf 'CRI endpoint: unix:///run/containerd/containerd.sock\n'
printf 'Node hostname: %s\n' "$(hostname)"
printf 'Swap active entries: '
swapon --show --noheadings | wc -l

echo
echo "Runtime completed successfully."
if command -v docker >/dev/null 2>&1; then
  echo "Docker/OctoPrint were preserved."
else
  echo "No Docker installation was present; containerd was prepared directly for KubeEdge."
fi
echo "No edge CNI was installed (intentional for the hostNetwork-only edge design)."
echo "Next: run edgecore-join.sh"