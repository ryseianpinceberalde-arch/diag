from datetime import datetime, timedelta, timezone
from services.status import effective_status, health_from_prediction


def test_effective_status_marks_stale_computer_offline():
    stale = datetime.now(timezone.utc) - timedelta(minutes=10)
    assert effective_status({"status": "online", "last_seen": stale.isoformat()}) == "offline"


def test_health_from_prediction_uses_risk_level():
    assert health_from_prediction({"risk_level": "critical"}, "online") == "critical"
    assert health_from_prediction({"risk_level": "medium"}, "online") == "warning"
    assert health_from_prediction({"risk_level": "low"}, "online") == "healthy"
    assert health_from_prediction({"risk_level": "critical"}, "offline") == "offline"
