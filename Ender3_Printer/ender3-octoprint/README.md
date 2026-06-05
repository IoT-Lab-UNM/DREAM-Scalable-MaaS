# Ender-3 OctoPrint Kubernetes Client

This image runs a Python OctoRest client from Kubernetes. It connects to an existing OctoPrint server, uploads `f4u2.gcode`, optionally selects it, and optionally starts the print.

The OctoPrint server itself is still expected to run on the Raspberry Pi connected to the Ender-3 printer, typically at `http://10.88.202.187:5000`.

## Files

```text
Dockerfile
requirements.txt
octoprint_client.py
gcode/f4u2.gcode
octoprint-secret.example.yaml
octoprint-configmap.yaml
octoprint-print-job.yaml
setup_ender3_octoprint.sh
```

## Safety note

The default `START_PRINT` value is `false`. This means the pod uploads and selects the G-code but does not start physical printing. Change it to `true` only when the printer is ready, supervised, connected, homed/calibrated, and safe to run.

## Build and deploy

```bash
cd ender3-octoprint-k8s

export OCTOPRINT_API_KEY='your_octoprint_api_key_here'

./setup_ender3_octoprint.sh
```

## Enable actual printing

Edit `octoprint-configmap.yaml`:

```yaml
START_PRINT: "true"
```

Then reapply and rerun the Job:

```bash
kubectl apply -f octoprint-configmap.yaml
kubectl -n microservices delete job ender3-octoprint-print-job --ignore-not-found=true
kubectl apply -f octoprint-print-job.yaml
kubectl -n microservices logs -f job/ender3-octoprint-print-job
```

## Verify

```bash
kubectl -n microservices get pods -l app=ender3-octoprint-client -o wide
kubectl -n microservices logs -f job/ender3-octoprint-print-job
```

## Update OctoPrint URL

Edit `octoprint-configmap.yaml` if the Raspberry Pi/OctoPrint IP changes:

```yaml
OCTOPRINT_URL: "http://10.88.202.187:5000"
```
