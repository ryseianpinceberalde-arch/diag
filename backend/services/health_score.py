from __future__ import annotations

from typing import Any


def _component_score(value: float | None, warning: float, critical: float) -> float | None:
    if value is None:
        return None
    if value >= critical:
        return 0
    if value <= warning:
        return 100
    return round((critical - value) / (critical - warning) * 100, 1)


def _inverse_component_score(value: float | None, warning: float, critical: float) -> float | None:
    if value is None:
        return None
    if value <= critical:
        return 0
    if value >= warning:
        return 100
    return round((value - critical) / (warning - critical) * 100, 1)


def calculate_health_score(reading: dict[str, Any] | None, inventory: dict[str, Any] | None = None) -> dict[str, Any]:
    reading = reading or {}
    inventory = inventory or {}
    factors: dict[str, float] = {}
    weights = {"cpu": 15, "memory": 15, "storage": 20, "temperature": 15, "battery": 10, "network": 10, "disk_smart": 15}

    for key, value, warning, critical in (
        ("cpu", reading.get("cpu_usage"), 80, 95),
        ("memory", reading.get("ram_usage"), 80, 95),
        ("storage", reading.get("disk_usage"), 85, 95),
        ("temperature", reading.get("cpu_temperature"), 80, 90),
        ("network", reading.get("packet_loss"), 2, 10),
    ):
        score = _component_score(value, warning, critical)
        if score is not None:
            factors[key] = score

    battery = reading.get("battery_health")
    if battery is not None:
        factors["battery"] = _inverse_component_score(battery, 70, 50) or 0
    disk_health = str(reading.get("disk_health") or "").lower()
    if disk_health:
        factors["disk_smart"] = 0 if disk_health in {"bad", "fail", "failed", "critical"} else 50 if disk_health == "warning" else 100

    active_weights = {key: weights[key] for key in factors}
    score = round(sum(factors[key] * active_weights[key] for key in factors) / sum(active_weights.values()), 1) if factors else None
    label = "Unknown" if score is None else "Excellent" if score >= 90 else "Healthy" if score >= 80 else "Warning" if score >= 65 else "Poor" if score >= 40 else "Critical"
    return {"score": score, "label": label, "factors": factors}
