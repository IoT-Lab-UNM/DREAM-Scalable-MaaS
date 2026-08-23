#!/usr/bin/env bash
set -Eeuo pipefail

# DREAM Ender-3 Raspberry Pi local-network recovery.
# Run with: sudo ./dream-printer-network-recover.sh
#
# This deliberately validates the internal MaaS path through CloudNode instead
# of treating the upstream gateway as the health target.

readonly CONNECTION_NAME="NETGEAR68-5G-2"
readonly WIFI_INTERFACE="wlan0"
readonly PRINTER_CIDR="10.12.10.78/23"
readonly PRINTER_IP="10.12.10.78"
readonly GATEWAY_IP="10.12.10.1"
readonly DNS_SERVERS="10.3.33.10,10.3.32.10"
readonly CLOUDNODE_IP="10.12.10.124"
readonly SLA_HEALTH_URL="http://10.12.10.124:30070/healthz"
readonly JOB_HEALTH_URL="http://10.12.10.124:30080/healthz"

readonly -a REQUIRED_SERVICES=(
  containerd
  edgecore
  openvswitch-switch
  dream-printer-sdn
  dream-printer-mapper
  octoprint_startup
)

log() {
  printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"
}

die() {
  log "ERROR: $*" >&2
  exit 1
}

if [[ ${EUID} -ne 0 ]]; then
  die "Run this script with sudo."
fi

command -v nmcli >/dev/null 2>&1 || die "nmcli is not installed."
command -v ip >/dev/null 2>&1 || die "iproute2 is not installed."
command -v ping >/dev/null 2>&1 || die "ping is not installed."
command -v curl >/dev/null 2>&1 || die "curl is not installed."

nmcli -t -f NAME connection show | grep -Fxq "$CONNECTION_NAME" ||
  die "NetworkManager profile '$CONNECTION_NAME' does not exist."

log "Enforcing persistent DREAM printer network profile."
nmcli connection modify "$CONNECTION_NAME" \
  connection.interface-name "$WIFI_INTERFACE" \
  connection.autoconnect yes \
  802-11-wireless.cloned-mac-address permanent \
  ipv4.method manual \
  ipv4.addresses "$PRINTER_CIDR" \
  ipv4.gateway "$GATEWAY_IP" \
  ipv4.dns "$DNS_SERVERS" \
  ipv4.never-default no

current_cidr="$(ip -4 -o address show dev "$WIFI_INTERFACE" 2>/dev/null | awk '{print $4}' | head -n1 || true)"

if [[ "$current_cidr" != "$PRINTER_CIDR" ]]; then
  log "Current address is '${current_cidr:-none}'; activating $CONNECTION_NAME."
  nmcli connection up "$CONNECTION_NAME" ifname "$WIFI_INTERFACE"
fi

for attempt in {1..15}; do
  current_cidr="$(ip -4 -o address show dev "$WIFI_INTERFACE" 2>/dev/null | awk '{print $4}' | head -n1 || true)"
  [[ "$current_cidr" == "$PRINTER_CIDR" ]] && break
  sleep 1
done

[[ "$current_cidr" == "$PRINTER_CIDR" ]] ||
  die "Expected $PRINTER_CIDR on $WIFI_INTERFACE, found '${current_cidr:-none}'."

if ! ping -c 2 -W 2 "$CLOUDNODE_IP" >/dev/null 2>&1; then
  log "CloudNode is not reachable; reconnecting Wi-Fi once."
  nmcli connection down "$CONNECTION_NAME" >/dev/null 2>&1 || true
  sleep 2
  nmcli connection up "$CONNECTION_NAME" ifname "$WIFI_INTERFACE"
  sleep 5
fi

ping -c 3 -W 2 "$CLOUDNODE_IP" >/dev/null 2>&1 ||
  die "CloudNode $CLOUDNODE_IP remains unreachable. Check the AP and upstream switch."

log "Internal network is healthy: $PRINTER_IP -> $CLOUDNODE_IP."

for unit in "${REQUIRED_SERVICES[@]}"; do
  if systemctl is-active --quiet "$unit"; then
    log "Service $unit is active."
  else
    log "Service $unit is inactive; starting it."
    systemctl start "$unit"
    systemctl is-active --quiet "$unit" || die "Service $unit did not become active."
  fi
done

sla_health="$(curl --fail --silent --show-error --connect-timeout 3 --max-time 8 "$SLA_HEALTH_URL")" ||
  die "SLA Intelligence health check failed."
job_health="$(curl --fail --silent --show-error --connect-timeout 3 --max-time 8 "$JOB_HEALTH_URL")" ||
  die "Job Manager health check failed."

log "SLA Intelligence: $sla_health"
log "Job Manager: $job_health"
log "DREAM printer node is ready."
