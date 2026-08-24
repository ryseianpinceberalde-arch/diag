from datetime import datetime, timezone

from services.health import evaluate_computer_health
from services.prediction import risk_level, score_readings
from services.settings import Thresholds


def test_risk_level_thresholds():
    assert risk_level(10) == "low"
    assert risk_level(40) == "medium"
    assert risk_level(70) == "high"
    assert risk_level(90) == "critical"


def test_cpu_consecutive_readings_raise_risk():
    history = [{"cpu_usage": 95, "ram_usage": 50, "disk_usage": 50} for _ in range(5)]
    result = score_readings(history[0], history, [])
    assert result["risk_score"] >= 25
    assert "CPU usage stayed above 90%" in result["reasons"][0]


def test_critical_measurement_does_not_produce_low_risk():
    thresholds = Thresholds()
    latest = {"disk_usage": 97, "ram_usage": 30}
    health = evaluate_computer_health({"status": "online", "last_seen": datetime.now(timezone.utc).isoformat()}, latest, thresholds)
    result = score_readings(latest, [latest], [], thresholds, health)
    assert result["risk_score"] >= thresholds.risk_warning_score
    assert result["risk_level"] in {"medium", "high", "critical"}
