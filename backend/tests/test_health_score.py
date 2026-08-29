from services.health_score import calculate_health_score


def test_health_score_omits_unavailable_optional_sensors():
    result = calculate_health_score({"cpu_usage": 20, "ram_usage": 30, "disk_usage": 40})
    assert result["score"] is not None
    assert "battery" not in result["factors"]
    assert "temperature" not in result["factors"]


def test_health_score_marks_bad_disk_smart_critical():
    result = calculate_health_score({"disk_health": "failed"})
    assert result["score"] == 0
    assert result["label"] == "Critical"
