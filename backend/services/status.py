from datetime import datetime, timedelta, timezone
from typing import Any

CONNECTION_LOST_AFTER_SECONDS = 30
OFFLINE_AFTER_SECONDS = 120


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def effective_status(computer: dict[str, Any], now: datetime | None = None, offline_after_seconds: int = OFFLINE_AFTER_SECONDS) -> str:
    now = now or datetime.now(timezone.utc)
    last_seen = parse_timestamp(computer.get("last_seen"))
    if not last_seen:
        return "offline"
    age = now - last_seen
    if age > timedelta(seconds=offline_after_seconds):
        return "offline"
    if age > timedelta(seconds=CONNECTION_LOST_AFTER_SECONDS):
        return "connection_lost"
    return computer.get("status") or "online"


def health_from_prediction(prediction: dict[str, Any] | None, status: str) -> str:
    if status == "offline":
        return "offline"
    if not prediction:
        return "healthy"
    level = prediction.get("risk_level")
    if level == "critical":
        return "critical"
    if level in {"high", "medium"}:
        return "warning"
    return "healthy"
