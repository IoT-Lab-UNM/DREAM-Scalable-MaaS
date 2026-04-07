# Troubleshooting and Debugging Log

This section captures the real errors encountered and the exact fixes.

## Error 1 — Placeholder key left in config

### Symptom

```text
Key is not the correct length or format: `HUB_PRIVATE_KEY`
Configuration parsing error
```

### Cause
The placeholder string `HUB_PRIVATE_KEY` was left in `/etc/wireguard/wg0.conf`.

### Fix
Replace placeholders with the **actual key contents**, not file paths.

Correct:

```ini
PrivateKey = actual_base64_key_here=
```

Incorrect:

```ini
PrivateKey = HUB_PRIVATE_KEY
PrivateKey = /home/petro/hub.key
```

---

## Error 2 — `wg0 already exists`

### Symptom

```text
wg-quick: `wg0' already exists
```

### Cause
The interface was manually created with `wg-quick up wg0`, then started again with `systemctl start wg-quick@wg0`.

### Fix
Use one control path at a time. Clean up first:

```bash
sudo wg-quick down wg0 2>/dev/null || true
sudo ip link delete wg0 2>/dev/null || true
sudo systemctl reset-failed wg-quick@wg0
```

Then either:

```bash
sudo wg-quick up wg0
```

or:

```bash
sudo systemctl start wg-quick@wg0
```

---

## Error 3 — Edge sends traffic but receives nothing

### Symptom

```text
transfer: 0 B received, 83.54 KiB sent
```

### Cause
No handshake. The Hub was not reachable on UDP `51820`.

### Real root cause
Laptop 1 was behind an Xfinity router. Port forwarding was required.

### Fix
Configure router port forwarding:

```text
UDP 51820 -> 10.0.0.7:51820
```

Also verify on Hub:

```bash
sudo ss -lunp | grep 51820
sudo ufw status
```

---

## Error 4 — Tunnel still fails when both laptops appear on same public IP path

### Symptom
No handshake, even though the public IP was reachable by ping.

### Cause
Testing while both devices were effectively under the same NAT / path can break the expected Internet reachability model.

### Fix
Move Laptop 2 to a **different network / ISP**.

In the working run, Laptop 2 used a different wireless network / Ultra Mobile, and the tunnel succeeded.

---

## Error 5 — Ubuntu pip installation blocked

### Symptom

```text
error: externally-managed-environment
```

### Cause
Ubuntu 24.04 blocks direct system pip installs by default (PEP 668).

### Fix
Use a virtual environment:

```bash
sudo apt-get install -y python3-venv python3-full
python3 -m venv ~/poc-venv
source ~/poc-venv/bin/activate
pip install paho-mqtt requests
```

---

## Error 6 — MinIO `403 Forbidden`

### Symptom

```text
403 Client Error: Forbidden for url: http://10.250.0.1:9000/prints/test.txt
```

### Cause
The `prints` bucket was private.

### Fix
Set bucket policy to public download:

```bash
mc alias set local http://127.0.0.1:9000 minioadmin minioadmin123
mc anonymous set download local/prints
mc anonymous get local/prints
```

---

## Error 7 — MinIO `400 Bad Request`

### Symptom

```text
400 Client Error: Bad Request for url: http://10.250.0.1:9000/prints/test.txt
```

### Cause
The Python agent was still sending HTTP Basic Auth to the S3 object endpoint on `:9000`.

### Fix
Remove `auth=(MINIO_USER, MINIO_PASS)` and use:

```python
r = requests.get(url, timeout=30)
```

The object endpoint works with:
- public object access,
- presigned URL,
- or S3-signed requests,

but **not** plain HTTP Basic Auth.

---

## Error 8 — NetworkManager popup: “activation network failed”

### Symptom
Ubuntu UI popup after `wg-quick up wg0`.

### Cause
NetworkManager tried to manage an interface created manually.

### Fix
It is mostly cosmetic. To silence it, create:

`/etc/NetworkManager/conf.d/wireguard.conf`

```ini
[keyfile]
unmanaged-devices=interface-name:wg0
```

Then restart NetworkManager:

```bash
sudo systemctl restart NetworkManager
```

---

## Working-state indicators

### Hub

```bash
sudo ss -lunp | grep 51820
sudo wg show
```

Expected:
- UDP `51820` listening
- peer present

### Edge

```bash
sudo wg show
ping -c 3 10.250.0.1
```

Expected:
- `latest handshake: ...`
- non-zero bytes received
- ping replies from `10.250.0.1`

### Final application check

Expected Edge agent output:

```text
Listening for jobs...
[DEBUG] Downloading: http://10.250.0.1:9000/prints/test.txt
[DEBUG] HTTP status: 200
[PRINT] Processing file: /tmp/print_jobs/job1-test.txt
```

