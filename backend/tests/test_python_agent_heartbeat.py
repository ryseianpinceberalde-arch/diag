import importlib.util
from pathlib import Path
import sys
import threading
from unittest.mock import Mock

import dotenv
import pytest


def test_heartbeat_continues_during_slow_collection_and_stops_on_agent_failure(monkeypatch):
    pytest.importorskip("psutil", reason="Requires the agent's requirements.txt")
    pytest.importorskip("requests", reason="Requires the agent's requirements.txt")
    # Load the agent without reading installation credentials or collecting hardware.
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setenv("AGENT_API_KEY", "test-key")
    monkeypatch.setattr(sys, "argv", ["agent.py", "--api-base-url", "https://example.invalid"])
    path = Path(__file__).resolve().parents[2] / "agent" / "agent.py"
    spec = importlib.util.spec_from_file_location("heartbeat_test_agent", path)
    agent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent)
    monkeypatch.setattr(agent, "check_api_health", lambda: True)
    monkeypatch.setattr(agent, "computer_metadata", lambda: {"device_id": "device-1"})
    monkeypatch.setattr(agent, "poll_agent_commands", lambda device_id: None)
    monkeypatch.setattr(agent.signal, "signal", lambda *args: None)
    queue = Mock()
    monkeypatch.setattr(agent, "Queue", lambda path: queue)
    monkeypatch.setattr(agent, "HEARTBEAT_INTERVAL_SECONDS", 0.01)
    sent, exited = threading.Event(), threading.Event()
    calls = []

    def post(endpoint, payload):
        if endpoint == "agents/heartbeat":
            calls.append(payload)
            if len(calls) == 1:
                return False  # A failed heartbeat must not stop later attempts.
            sent.set()
        return True

    original_sender = agent.send_heartbeats

    def sender(*args):
        try:
            original_sender(*args)
        finally:
            exited.set()

    def collect(device_id):
        assert sent.wait(2), "Sensor collection blocked heartbeats"
        raise RuntimeError("simulated sensor failure")

    monkeypatch.setattr(agent, "post", post)
    monkeypatch.setattr(agent, "send_heartbeats", sender)
    monkeypatch.setattr(agent, "collect_reading", collect)
    with pytest.raises(RuntimeError, match="simulated sensor failure"):
        agent.main()
    assert exited.is_set()
    assert len(calls) >= 2
    assert all(call == {"device_id": "device-1", "heartbeat_only": True} for call in calls)
    queue.add.assert_not_called()
