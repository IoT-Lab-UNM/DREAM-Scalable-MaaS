# How to Push This Material to `IoT-lab-UNM/DREAM-Project`

Repository:

```text
https://github.com/IoT-lab-UNM/DREAM-Project
```

Because the repository has **multiple branches**, use a safe branch workflow.

## 1. Clone the repository

```bash
git clone https://github.com/IoT-lab-UNM/DREAM-Project.git
cd DREAM-Project
```

## 2. Inspect branches

```bash
git fetch --all --prune
git branch -a
```

Pick the correct base branch, for example:

```bash
git checkout main
```

or another project branch if that is your normal integration branch.

## 3. Update local copy

```bash
git pull origin <base-branch>
```

Example:

```bash
git pull origin main
```

## 4. Create a dedicated feature/documentation branch

```bash
git checkout -b docs/poc-overlay-wireguard-minio-mqtt
```

## 5. Create target folders in the repo

Example structure inside the existing repo:

```bash
mkdir -p docs/poc scripts/poc/hub scripts/poc/edge configs/poc/hub configs/poc/edge docker/poc edge/poc
```

## 6. Copy this package into the repo

Example:

```bash
cp /path/to/DREAM-Project-poc/README.md docs/poc/README-overlay-wireguard-minio-mqtt.md
cp /path/to/DREAM-Project-poc/docs/*.md docs/poc/
cp /path/to/DREAM-Project-poc/scripts/hub/* scripts/poc/hub/
cp /path/to/DREAM-Project-poc/scripts/edge/* scripts/poc/edge/
cp /path/to/DREAM-Project-poc/configs/hub/* configs/poc/hub/
cp /path/to/DREAM-Project-poc/configs/edge/* configs/poc/edge/
cp /path/to/DREAM-Project-poc/docker/* docker/poc/
cp /path/to/DREAM-Project-poc/edge/* edge/poc/
```

## 7. Review before commit

```bash
git status
git diff --staged
```

## 8. Make sure no secrets are present

Do **not** commit:
- real private keys,
- real `.mc` configs,
- `.venv` or `poc-venv`,
- downloaded objects,
- shell histories.

Recommended `.gitignore` entries if needed:

```text
*.key
*.pub
poc-venv/
venv/
__pycache__/
/tmp/print_jobs/
```

## 9. Commit changes

```bash
git add docs/poc scripts/poc configs/poc docker/poc edge/poc
git commit -m "Add reproducible 2-laptop overlay VPN POC with WireGuard, MinIO, and MQTT"
```

## 10. Push the branch

```bash
git push -u origin docs/poc-overlay-wireguard-minio-mqtt
```

## 11. Open a pull request

In GitHub:
- open the repository,
- switch to your pushed branch,
- create a Pull Request,
- target the correct base branch.

## 12. Suggested PR title

```text
Add reproducible 2-laptop overlay VPN POC with WireGuard, MinIO, and MQTT
```

## 13. Suggested PR description

```text
This PR adds a complete, reproducible proof of concept for a 2-laptop overlay-only site-to-cloud architecture using WireGuard, MinIO, and MQTT.

Included:
- infrastructure and application-layer documentation,
- working config templates,
- helper scripts,
- edge processing agent,
- troubleshooting notes from real deployment,
- branch-safe reproduction and push instructions.
```

