from datetime import datetime, timedelta, timezone
import pytest

from services.health import evaluate_computer_health
from services.settings import Thresholds, validate_threshold_update
from services.status import effective_status, health_from_prediction


def test_effective_status_marks_stale_computer_offline():
    stale = datetime.now(timezone.utc) - timedelta(minutes=10)
    assert effective_status({"status": "online", "last_seen": stale.isoformat()}) == "offline"


def test_health_from_prediction_uses_risk_level():
    assert health_from_prediction({"risk_level": "critical"}, "online") == "critical"
    assert health_from_prediction({"risk_level": "medium"}, "online") == "warning"
    assert health_from_prediction({"risk_level": "low"}, "online") == "healthy"
    assert health_from_prediction({"risk_level": "critical"}, "offline") == "offline"


def test_health_engine_marks_offline_computer():
    stale = datetime.now(timezone.utc) - timedelta(minutes=10)
    result = evaluate_computer_health({"status": "online", "last_seen": stale.isoformat()}, None, Thresholds())
    assert result["status"] == "offline"
    assert result["issues"][0]["alert_key"] == "agent:offline"


def test_disk_usage_above_critical_creates_critical_issue():
    result = evaluate_computer_health(
        {"status": "online", "last_seen": datetime.now(timezone.utc).isoformat()},
        {"disk_usage": 97, "ram_usage": 30},
        Thresholds(),
    )
    assert result["status"] == "critical"
    issue = next(issue for issue in result["issues"] if issue["component"] == "disk")
    assert issue["severity"] == "critical"
    assert issue["alert_key"] == "disk:usage_high"


def test_ram_usage_above_warning_creates_warning_issue():
    result = evaluate_computer_health(
        {"status": "online", "last_seen": datetime.now(timezone.utc).isoformat()},
        {"ram_usage": 90, "disk_usage": 20},
        Thresholds(),
    )
    assert result["status"] == "warning"
    issue = next(issue for issue in result["issues"] if issue["component"] == "memory")
    assert issue["severity"] == "high"
    assert issue["alert_key"] == "memory:usage_high"


def test_repeated_telemetry_uses_stable_alert_key_for_deduplication():
    computer = {"status": "online", "last_seen": datetime.now(timezone.utc).isoformat()}
    first = evaluate_computer_health(computer, {"disk_usage": 97}, Thresholds())
    second = evaluate_computer_health(computer, {"disk_usage": 98}, Thresholds())
    assert first["issues"][0]["alert_key"] == second["issues"][0]["alert_key"]


def test_recovered_measurement_has_no_active_issue():
    computer = {"status": "online", "last_seen": datetime.now(timezone.utc).isoformat()}
    result = evaluate_computer_health(computer, {"disk_usage": 40, "ram_usage": 20}, Thresholds())
    assert result["status"] == "healthy"
    assert result["issues"] == []


def test_settings_validation_rejects_unsafe_values():
    with pytest.raises(ValueError):
        validate_threshold_update({"disk_warning_percent": 99, "disk_critical_percent": 95})
