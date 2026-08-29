import pytest

from schemas.models import AgentTelemetry


def payload(**overrides):
    value = {
        "device_id": "device-123",
        "cpu": {"usage_percent": 25},
        "memory": {"usage_percent": 50},
        "storage": [{"usage_percent": 60}],
        "battery": None,
        "temperature": {"available": False, "temperatureC": None},
        "processes": [{"name": "explorer", "pid": 1}],
    }
    value.update(overrides)
    return value


def test_telemetry_accepts_desktop_without_battery():
    assert AgentTelemetry.model_validate(payload()).battery is None


def test_telemetry_rejects_out_of_range_percentages():
    with pytest.raises(ValueError):
        AgentTelemetry.model_validate(payload(cpu={"usage_percent": 101}))


def test_telemetry_rejects_more_than_fifteen_processes():
    with pytest.raises(ValueError):
        AgentTelemetry.model_validate(payload(processes=[{"name": str(i)} for i in range(16)]))


def test_telemetry_rejects_process_command_data():
    with pytest.raises(ValueError):
        AgentTelemetry.model_validate(payload(processes=[{"name": "x", "command_line": "secret"}]))
