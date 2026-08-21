import json
import urllib.error
import urllib.request


class PolicyUnavailable(RuntimeError):
    pass


class PolicyProtocolError(RuntimeError):
    pass


class PolicyClient:
    def __init__(self, base_url, timeout_seconds=3.0):
        self.evaluate_url = base_url.rstrip("/") + "/api/v1/policy/evaluate"
        self.timeout_seconds = float(timeout_seconds)

    def evaluate(self, payload):
        request = urllib.request.Request(
            self.evaluate_url,
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                body = response.read(1024 * 1024)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise PolicyUnavailable(str(exc)) from exc

        try:
            result = json.loads(body)
        except (TypeError, ValueError, UnicodeDecodeError) as exc:
            raise PolicyProtocolError("policy response is not valid JSON") from exc

        if not isinstance(result, dict):
            raise PolicyProtocolError("policy response must be a JSON object")
        if result.get("decision") not in {"ALLOW", "DENY"}:
            raise PolicyProtocolError("policy response has no valid decision")
        if not result.get("decision_id") or not result.get("policy_version"):
            raise PolicyProtocolError("policy response lacks audit identifiers")
        return result
