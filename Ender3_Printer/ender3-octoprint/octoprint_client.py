import os
import sys
import time
from pathlib import Path

from octorest import OctoRest


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def main() -> int:
    octoprint_url = os.getenv("OCTOPRINT_URL", "http://10.88.188.190:5000").rstrip("/")
    api_key = os.getenv("OCTOPRINT_API_KEY")
    gcode_path = Path(os.getenv("GCODE_PATH", "/app/gcode/f4u2.gcode"))
    start_print = env_bool("START_PRINT", False)
    select_after_upload = env_bool("SELECT_AFTER_UPLOAD", True)
    wait_seconds = int(os.getenv("WAIT_AFTER_UPLOAD_SECONDS", "2"))

    if not api_key:
        print("ERROR: OCTOPRINT_API_KEY environment variable is required.", file=sys.stderr)
        return 2

    if not gcode_path.exists():
        print(f"ERROR: G-code file not found: {gcode_path}", file=sys.stderr)
        return 3

    print(f"[Ender3 Client] Connecting to OctoPrint at {octoprint_url}")
    client = OctoRest(url=octoprint_url, apikey=api_key)

    print("[Ender3 Client] OctoPrint version:")
    print(client.version)

    print("[Ender3 Client] Printer status:")
    try:
        print(client.printer())
    except TypeError:
        print(client.printer)

    print(f"[Ender3 Client] Uploading G-code: {gcode_path.name}")
    client.upload(str(gcode_path))

    if wait_seconds > 0:
        time.sleep(wait_seconds)

    if select_after_upload:
        print(f"[Ender3 Client] Selecting file: {gcode_path.name}")
        client.select(gcode_path.name, print=start_print)

    if start_print:
        print("[Ender3 Client] Print job started.")
    else:
        print("[Ender3 Client] Upload completed. START_PRINT=false, so the printer was NOT started.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
