from services.prediction import risk_level, score_readings


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
