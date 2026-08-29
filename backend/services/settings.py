from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from supabase import Client


@dataclass(frozen=True)
class Thresholds:
    offline_after_seconds: int = 120
    agent_reporting_interval_seconds: int = 10
    disk_warning_percent: float = 85
    disk_critical_percent: float = 95
    ram_warning_percent: float = 85
    ram_critical_percent: float = 95
    cpu_temperature_warning_c: float = 80
    cpu_temperature_critical_c: float = 90
    packet_loss_warning_percent: float = 5
    packet_loss_critical_percent: float = 10
    latency_warning_ms: float = 200
    latency_critical_ms: float = 500
    risk_warning_score: int = 35
    risk_critical_score: int = 75
    alert_recovery_readings: int = 2
    data_retention_days: int = 365
    notifications_enabled: bool = False
    notification_recipients: tuple[str, ...] = ()


DEFAULT_THRESHOLDS = Thresholds()


def default_threshold_dict() -> dict[str, Any]:
    return asdict(DEFAULT_THRESHOLDS)


def coerce_number(value: Any, fallback: int | float) -> int | float:
    if value is None:
        return fallback
    if isinstance(value, dict) and "value" in value:
        value = value["value"]
    try:
        if isinstance(fallback, int) and not isinstance(fallback, bool):
            return int(value)
        return float(value)
    except (TypeError, ValueError):
        return fallback


def coerce_setting(value: Any, fallback: Any) -> Any:
    if isinstance(fallback, bool):
        if isinstance(value, dict) and "value" in value:
            value = value["value"]
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)
    if isinstance(fallback, tuple):
        if isinstance(value, dict) and "value" in value:
            value = value["value"]
        if isinstance(value, str):
            return tuple(item.strip() for item in value.split(",") if item.strip())
        if isinstance(value, list):
            return tuple(str(item).strip() for item in value if str(item).strip())
        return fallback
    return coerce_number(value, fallback)


def load_thresholds(client: Client | None = None) -> Thresholds:
    values = default_threshold_dict()
    if client is not None:
        try:
            rows = client.table("app_settings").select("key,value").execute().data or []
            for row in rows:
                key = row.get("key")
                if key in values:
                    values[key] = coerce_setting(row.get("value"), values[key])
        except Exception:
            pass
    return Thresholds(**values)


def validate_threshold_update(values: dict[str, Any]) -> dict[str, Any]:
    allowed = default_threshold_dict()
    clean: dict[str, Any] = {}
    for key, value in values.items():
        if key not in allowed:
            continue
        coerced = coerce_setting(value, allowed[key])
        if isinstance(coerced, (int, float)) and not isinstance(coerced, bool) and coerced < 0:
            raise ValueError(f"{key} cannot be negative")
        clean[key] = coerced

    pairs = (
        ("disk_warning_percent", "disk_critical_percent"),
        ("ram_warning_percent", "ram_critical_percent"),
        ("cpu_temperature_warning_c", "cpu_temperature_critical_c"),
        ("packet_loss_warning_percent", "packet_loss_critical_percent"),
        ("risk_warning_score", "risk_critical_score"),
    )
    merged = {**allowed, **clean}
    for warning_key, critical_key in pairs:
        if merged[warning_key] >= merged[critical_key]:
            raise ValueError(f"{warning_key} must be lower than {critical_key}")
    if merged["offline_after_seconds"] < 60:
        raise ValueError("offline_after_seconds must be at least 60")
    if merged["agent_reporting_interval_seconds"] < 10:
        raise ValueError("agent_reporting_interval_seconds must be at least 10")
    if merged["alert_recovery_readings"] < 1:
        raise ValueError("alert_recovery_readings must be at least 1")
    return clean
