import json
from datetime import datetime, timezone


class SLAConfigurationError(ValueError):
    pass


class SLARequestError(ValueError):
    pass


def utcnow():
    return datetime.now(timezone.utc)


def iso_now():
    return utcnow().isoformat().replace("+00:00", "Z")


def parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def load_configuration(path):
    with open(path, encoding="utf-8") as stream:
        config = json.load(stream)
    if not isinstance(config, dict) or not config.get("version"):
        raise SLAConfigurationError("configuration requires version")
    classes = config.get("classes")
    if not isinstance(classes, dict) or not classes:
        raise SLAConfigurationError("configuration requires SLA classes")
    required = {
        "max_freshness_age_seconds",
        "min_score",
        "require_network_telemetry",
        "max_telemetry_age_seconds",
        "max_rtt_ms",
        "max_loss_percent",
        "max_jitter_ms",
        "max_queue_depth",
    }
    for name, profile in classes.items():
        if not isinstance(profile, dict) or not required.issubset(profile):
            raise SLAConfigurationError(f"SLA class {name!r} is incomplete")
    return config


def _number(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _telemetry_age(telemetry, now):
    observed_at = parse_time((telemetry or {}).get("observed_at"))
    if observed_at is None:
        return None
    return max(0.0, (now - observed_at).total_seconds())


class SLAEngine:
    def __init__(self, configuration):
        self.configuration = configuration

    def evaluate(self, payload, telemetry=None, now=None):
        if not isinstance(payload, dict):
            raise SLARequestError("request must be a JSON object")
        request_id = str(payload.get("request_id") or "").strip()
        job = payload.get("job")
        context = payload.get("context")
        if not request_id or not isinstance(job, dict) or not isinstance(context, dict):
            raise SLARequestError("request_id, job, and context are required")

        sla_class = str(job.get("sla_class") or "").strip()
        profile = self.configuration["classes"].get(sla_class)
        if profile is None:
            return self._result(
                request_id,
                job,
                sla_class,
                "REJECT",
                0,
                "HIGH",
                ["unknown_sla_class"],
                {},
                {},
            )

        now = now or utcnow()
        readiness = context.get("readiness") or {}
        reasons = []
        eligible = readiness.get("eligible") is True
        if not eligible:
            reasons.append("device_not_eligible")

        freshness_age = _number(readiness.get("freshness_age_seconds"))
        max_freshness = float(profile["max_freshness_age_seconds"])
        if freshness_age is None:
            reasons.append("freshness_missing")
        elif freshness_age > max_freshness:
            reasons.append("freshness_slo_exceeded")

        telemetry = telemetry if isinstance(telemetry, dict) else {}
        metrics = telemetry.get("metrics") if isinstance(telemetry.get("metrics"), dict) else {}
        telemetry_age = _telemetry_age(telemetry, now)
        network_fields = ("rtt_ms", "loss_percent", "jitter_ms")
        network_present = all(_number(metrics.get(name)) is not None for name in network_fields)
        if profile["require_network_telemetry"] and not network_present:
            reasons.append("network_telemetry_required")
        if telemetry and telemetry_age is None:
            reasons.append("telemetry_timestamp_invalid")
        elif telemetry_age is not None and telemetry_age > float(profile["max_telemetry_age_seconds"]):
            reasons.append("telemetry_stale")

        limits = {
            "rtt_ms": float(profile["max_rtt_ms"]),
            "loss_percent": float(profile["max_loss_percent"]),
            "jitter_ms": float(profile["max_jitter_ms"]),
            "queue_depth": float(profile["max_queue_depth"]),
        }
        for metric, limit in limits.items():
            value = _number(metrics.get(metric))
            if value is not None and value > limit:
                reasons.append(f"{metric}_slo_exceeded")

        health_score = 50.0 if eligible else 0.0
        if freshness_age is None:
            freshness_score = 0.0
        else:
            freshness_score = 30.0 * max(0.0, 1.0 - freshness_age / max_freshness)
        network_score = self._group_score(metrics, limits, network_fields, 10.0)
        queue_score = self._group_score(metrics, limits, ("queue_depth",), 10.0)
        score = round(max(0.0, min(100.0, health_score + freshness_score + network_score + queue_score)), 2)
        if score < float(profile["min_score"]):
            reasons.append("minimum_score_not_met")

        reasons = list(dict.fromkeys(reasons))
        decision = "ADMIT" if not reasons else "REJECT"
        risk = "LOW" if decision == "ADMIT" and score >= 85 else "MEDIUM" if decision == "ADMIT" else "HIGH"
        observations = {
            "device_eligible": eligible,
            "freshness_age_seconds": freshness_age,
            "telemetry_age_seconds": None if telemetry_age is None else round(telemetry_age, 3),
            "network_telemetry_present": network_present,
            "metrics": {name: _number(metrics.get(name)) for name in limits},
        }
        thresholds = {**limits, "max_freshness_age_seconds": max_freshness, "minimum_score": float(profile["min_score"])}
        return self._result(
            request_id,
            job,
            sla_class,
            decision,
            score,
            risk,
            reasons or ["sla_targets_met"],
            observations,
            thresholds,
        )

    @staticmethod
    def _group_score(metrics, limits, names, weight):
        values = [_number(metrics.get(name)) for name in names]
        if all(value is None for value in values):
            return weight
        ratios = []
        for name, value in zip(names, values):
            if value is not None:
                limit = limits[name]
                ratios.append(max(0.0, 1.0 - value / limit) if limit > 0 else 0.0)
        return weight * (sum(ratios) / len(ratios)) if ratios else 0.0

    def _result(self, request_id, job, sla_class, decision, score, risk, reasons, observations, thresholds):
        return {
            "decision": decision,
            "decision_id": f"sla-{request_id}",
            "request_id": request_id,
            "sla_version": self.configuration["version"],
            "sla_class": sla_class,
            "job_id": job.get("id"),
            "command_id": job.get("command_id"),
            "device_id": job.get("device_id"),
            "score": score,
            "risk": risk,
            "reason_codes": reasons,
            "observations": observations,
            "thresholds": thresholds,
            "evaluated_at": iso_now(),
        }
