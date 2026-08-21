import json
from pathlib import Path


class PolicyConfigurationError(RuntimeError):
    pass


class PolicyRequestError(ValueError):
    pass


class PolicyEngine:
    def __init__(self, policy_path):
        self.policy_path = Path(policy_path)

    def policy(self):
        try:
            value = json.loads(self.policy_path.read_text())
        except (OSError, ValueError) as exc:
            raise PolicyConfigurationError(str(exc)) from exc

        if not isinstance(value, dict):
            raise PolicyConfigurationError("policy document must be an object")
        if not value.get("version"):
            raise PolicyConfigurationError("policy version is required")
        if value.get("default_effect") not in {"ALLOW", "DENY"}:
            raise PolicyConfigurationError("default_effect must be ALLOW or DENY")
        if not isinstance(value.get("rules"), list):
            raise PolicyConfigurationError("policy rules must be a list")

        list_fields = {
            "device_ids",
            "device_kinds",
            "actions",
            "sla_classes",
        }
        for index, rule in enumerate(value["rules"]):
            if not isinstance(rule, dict):
                raise PolicyConfigurationError(f"rule {index} must be an object")
            if not rule.get("id"):
                raise PolicyConfigurationError(f"rule {index} requires an id")
            if rule.get("effect") not in {"ALLOW", "DENY"}:
                raise PolicyConfigurationError(
                    f"rule {rule['id']} has an invalid effect"
                )
            match = rule.get("match", {})
            if not isinstance(match, dict):
                raise PolicyConfigurationError(
                    f"rule {rule['id']} match must be an object"
                )
            for field in list_fields:
                if field in match and not isinstance(match[field], list):
                    raise PolicyConfigurationError(
                        f"rule {rule['id']} {field} must be a list"
                    )
            if not isinstance(match.get("required_parameters", {}), dict):
                raise PolicyConfigurationError(
                    f"rule {rule['id']} required_parameters must be an object"
                )
            if not isinstance(rule.get("reason_codes", []), list):
                raise PolicyConfigurationError(
                    f"rule {rule['id']} reason_codes must be a list"
                )
        return value

    @staticmethod
    def _validate_request(value):
        if not isinstance(value, dict):
            raise PolicyRequestError("request must be a JSON object")
        job = value.get("job")
        if not isinstance(job, dict):
            raise PolicyRequestError("job must be a JSON object")
        required = {
            "id",
            "command_id",
            "device_id",
            "device_kind",
            "action",
        }
        missing = sorted(key for key in required if not job.get(key))
        if missing:
            raise PolicyRequestError(
                "missing required job fields: " + ",".join(missing)
            )
        if not isinstance(job.get("parameters", {}), dict):
            raise PolicyRequestError("job.parameters must be a JSON object")
        return job

    @staticmethod
    def _matches(rule, job, context):
        match = rule.get("match", {})
        if not isinstance(match, dict):
            return False

        list_fields = {
            "device_ids": "device_id",
            "device_kinds": "device_kind",
            "actions": "action",
            "sla_classes": "sla_class",
        }
        for rule_field, job_field in list_fields.items():
            allowed = match.get(rule_field)
            if allowed is not None and job.get(job_field) not in allowed:
                return False

        required_parameters = match.get("required_parameters", {})
        if not isinstance(required_parameters, dict):
            return False
        parameters = job.get("parameters", {})
        for key, expected in required_parameters.items():
            if parameters.get(key) != expected:
                return False

        if match.get("require_eligible"):
            readiness = context.get("readiness", {})
            if readiness.get("eligible") is not True:
                return False

        return True

    def evaluate(self, value):
        job = self._validate_request(value)
        context = value.get("context", {})
        if not isinstance(context, dict):
            raise PolicyRequestError("context must be a JSON object")

        policy = self.policy()
        for rule in policy["rules"]:
            if not isinstance(rule, dict) or not rule.get("enabled", True):
                continue
            if self._matches(rule, job, context):
                effect = rule.get("effect")
                if effect not in {"ALLOW", "DENY"}:
                    raise PolicyConfigurationError(
                        f"rule {rule.get('id', 'unknown')} has an invalid effect"
                    )
                return {
                    "decision": effect,
                    "matched_policy": rule.get("id", "unnamed-rule"),
                    "reason_codes": rule.get(
                        "reason_codes",
                        ["matched_policy_rule"],
                    ),
                    "policy_version": policy["version"],
                }

        return {
            "decision": policy["default_effect"],
            "matched_policy": "default",
            "reason_codes": ["no_matching_policy_rule"],
            "policy_version": policy["version"],
        }
