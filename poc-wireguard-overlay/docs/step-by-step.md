# Step-by-Step Reproduction Guide

## 1. Install WireGuard on both laptops

```bash
sudo apt-get update
sudo apt-get install -y wireguard curl iptables
```

## 2. Enable IPv4 forwarding on both laptops

```bash
sudo sysctl -w net.ipv4.ip_forward=1
echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf
```

## 3. Generate WireGuard keys

### Hub

```bash
umask 077
wg genkey | tee ~/hub.key | wg pubkey > ~/hub.pub
cat ~/hub.pub
cat ~/hub.key
```

### Edge

```bash
umask 077
wg genkey | tee ~/edge.key | wg pubkey > ~/edge.pub
cat ~/edge.pub
cat ~/edge.key
```

## 4. Configure the Hub

Create `/etc/wireguard/wg0.conf`:

```ini
[Interface]
Address = 10.250.0.1/16
ListenPort = 51820
PrivateKey = HUB_PRIVATE_KEY

[Peer]
PublicKey = EDGE_PUBLIC_KEY
AllowedIPs = 10.250.1.1/32
```

Set permissions:

```bash
sudo chmod 600 /etc/wireguard/wg0.conf
```

Allow firewall:

```bash
sudo ufw allow 51820/udp
sudo ufw status
```

Bring the interface up:

```bash
sudo wg-quick down wg0 2>/dev/null || true
sudo ip link delete wg0 2>/dev/null || true
sudo wg-quick up wg0
sudo wg show
ip addr show wg0
```

### Expected good output

- `interface: wg0`
- `listening port: 51820`
- `inet 10.250.0.1/16 scope global wg0`

## 5. Configure Hub-side router

**Do not use Port Triggering.** Use **Port Forwarding / Virtual Server**.

Required rule:

```text
Protocol: UDP
External Port: 51820
Internal IP: <Hub LAN IP, e.g. 10.0.0.7>
Internal Port: 51820
```

## 6. Configure the Edge

Create `/etc/wireguard/wg0.conf`:

```ini
[Interface]
Address = 10.250.1.1/32
PrivateKey = EDGE_PRIVATE_KEY

[Peer]
PublicKey = HUB_PUBLIC_KEY
Endpoint = HUB_PUBLIC_IP:51820
AllowedIPs = 10.250.0.1/32
PersistentKeepalive = 25
```

Set permissions:

```bash
sudo chmod 600 /etc/wireguard/wg0.conf
```

Bring it up:

```bash
sudo wg-quick down wg0 2>/dev/null || true
sudo ip link delete wg0 2>/dev/null || true
sudo wg-quick up wg0
sudo wg show
```

## 7. Verify VPN handshake

On Edge:

```bash
sudo wg show
ping -c 3 10.250.0.1
```

Expected working indicators:

- `latest handshake: ...`
- `transfer: <received> B, <sent> B`
- ping replies from `10.250.0.1`

## 8. Install Docker and cloud services on the Hub

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
mkdir -p ~/cloud-services
cd ~/cloud-services
```

Create `docker-compose.yml` and `mosquitto.conf` from this package.

Start services:

```bash
cd ~/cloud-services
docker compose up -d
docker ps
```

## 9. Open MinIO console

From the Edge browser:

```text
http://10.250.0.1:9001
```

Login:

- username: `minioadmin`
- password: `minioadmin123`

Create bucket:

```text
prints
```

Upload `test.txt`.

## 10. Set `prints` bucket to public read

Install MinIO CLI on the Hub:

```bash
curl -fsSL https://dl.min.io/client/mc/release/linux-amd64/mc -o ~/mc
chmod +x ~/mc
sudo mv ~/mc /usr/local/bin/mc
mc --version
```

Configure alias:

```bash
mc alias set local http://127.0.0.1:9000 minioadmin minioadmin123
```

Verify bucket:

```bash
mc ls local
```

Enable anonymous download:

```bash
mc anonymous set download local/prints
mc anonymous get local/prints
```

### Important note
Use `mc` **without** `sudo`. `sudo mc ...` may fail because root does not have the alias configured.

## 11. Install Edge tools

```bash
sudo apt-get update
sudo apt-get install -y mosquitto-clients python3 python3-pip python3-venv python3-full curl
python3 -m venv ~/poc-venv
source ~/poc-venv/bin/activate
pip install paho-mqtt requests
```

## 12. Save the working edge agent

Use `edge/print_agent.py` from this package as `~/print_agent.py`.

Run it:

```bash
source ~/poc-venv/bin/activate
python3 ~/print_agent.py
```

## 13. Publish a test job

In another terminal on the Edge:

```bash
mosquitto_pub -h 10.250.0.1 -t print/jobs -m '{"job_id":"job1","object":"prints/test.txt","target_site":"EDGE1"}'
```

### Expected result

Agent terminal:

```text
Listening for jobs...
[DEBUG] Downloading: http://10.250.0.1:9000/prints/test.txt
[DEBUG] HTTP status: 200
[PRINT] Processing file: /tmp/print_jobs/job1-test.txt
```

## 14. Verify downloaded file

```bash
ls -l /tmp/print_jobs
cat /tmp/print_jobs/job1-test.txt
```

