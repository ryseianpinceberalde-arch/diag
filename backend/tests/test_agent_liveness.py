import hashlib
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from config import Settings, get_settings
from database import get_supabase_admin
from dependencies import admin_client
from routers import agents, ingestion
from services import offline
from services.settings import Thresholds


class MemoryQuery:
    def __init__(self, database, table):
        self.database, self.table_name = database, table
        self.filters = []
        self.operation, self.value, self.single_row = "select", None, False

    def select(self, *args):
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def is_(self, key, value):
        assert value == "null"
        return self.eq(key, None)

    def limit(self, *args):
        return self

    def single(self):
        self.single_row = True
        return self

    def update(self, value):
        self.operation, self.value = "update", value
        return self

    def insert(self, value):
        self.operation, self.value = "insert", value
        return self

    def execute(self):
        rows = self.database.rows[self.table_name]
        if self.operation == "insert":
            row = deepcopy(self.value)
            rows.append(row)
            return SimpleNamespace(data=[deepcopy(row)])
        if self.operation == "update" and self.database.before_update:
            self.database.before_update()
        matched = [row for row in rows if all(row.get(key) == value for key, value in self.filters)]
        if self.operation == "update":
            if "computer_name" in self.value and self.value["computer_name"] is None:
                raise ValueError("computer_name violates NOT NULL constraint")
            for row in matched:
                row.update(deepcopy(self.value))
        data = deepcopy(matched)
        return SimpleNamespace(data=data[0] if self.single_row else data)


class MemoryDatabase:
    def __init__(self):
        self.before_update = None
        self.rows = {
            "computers": [
                {"id": f"computer-{number}", "device_id": f"device-{number}",
                 "computer_name": f"PC{number}", "status": "warning",
                 "agent_token_hash": hashlib.sha256(f"token-{number}".encode()).hexdigest(),
                 "last_seen": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()}
                for number in (1, 2)
            ],
            "diagnostic_readings": [],
        }

    def table(self, name):
        return MemoryQuery(self, name)


@pytest.fixture
def client_and_database(monkeypatch):
    database = MemoryDatabase()
    settings = Settings(
        _env_file=None, SUPABASE_URL="https://example.supabase.co",
        SUPABASE_ANON_KEY="test-anon", SUPABASE_SERVICE_ROLE_KEY="test-service",
        AGENT_API_KEY="test-key",
    )
    app = FastAPI()
    app.include_router(agents.router, prefix="/api/agents")
    app.include_router(ingestion.router, prefix="/api")
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[admin_client] = lambda: database
    app.dependency_overrides[get_supabase_admin] = lambda: database
    monkeypatch.setattr(ingestion, "upsert_health_alerts", lambda *args: {})
    monkeypatch.setattr(ingestion, "upsert_prediction_alerts", lambda *args: {})
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, database


def test_two_agents_can_heartbeat_independently_with_same_install_key(client_and_database):
    client, database = client_and_database
    before = datetime.now(timezone.utc)

    def send(number):
        for _ in range(3):
            response = client.post("/api/agents/heartbeat", headers={"X-Agent-Api-Key": "test-key"},
                                   json={"device_id": f"device-{number}", "heartbeat_only": True})
            assert response.status_code == 200, response.text

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(send, (1, 2)))
    for number, row in enumerate(database.rows["computers"], 1):
        assert row["computer_name"] == f"PC{number}"
        assert row["status"] == "warning"
        assert datetime.fromisoformat(row["last_seen"]) >= before
        assert row["last_heartbeat"] == row["last_seen"]
    assert database.rows["diagnostic_readings"] == []


def test_device_token_cannot_heartbeat_another_computer(client_and_database):
    client, database = client_and_database
    before = deepcopy(database.rows)
    response = client.post("/api/agents/heartbeat", headers={"Authorization": "Bearer token-1"},
                           json={"device_id": "device-2", "heartbeat_only": True})
    assert response.status_code == 403
    assert database.rows == before
    response = client.post("/api/agents/heartbeat", headers={"Authorization": "Bearer token-1"},
                           json={"device_id": "device-1", "heartbeat_only": True})
    assert response.status_code == 200


def test_heartbeat_requires_credentials_and_registered_device(client_and_database):
    client, _ = client_and_database
    data = {"device_id": "unknown-device", "heartbeat_only": True}
    assert client.post("/api/agents/heartbeat", json=data).status_code == 401
    assert client.post("/api/agents/heartbeat", json=data,
                       headers={"X-Agent-Api-Key": "test-key"}).status_code == 404


def test_lightweight_heartbeat_uses_server_time_and_recovers_offline_device(client_and_database):
    client, database = client_and_database
    database.rows["computers"][0]["status"] = "offline"
    before = datetime.now(timezone.utc)
    response = client.post("/api/agents/heartbeat", headers={"X-Agent-Api-Key": "test-key"}, json={
        "device_id": "device-1", "heartbeat_only": True,
        "last_heartbeat": (before - timedelta(days=1)).isoformat(),
    })
    assert response.status_code == 200, response.text
    row = database.rows["computers"][0]
    assert datetime.fromisoformat(row["last_seen"]) >= before
    assert row["status"] == "online"


@pytest.mark.parametrize("endpoint", ["heartbeat", "telemetry"])
def test_full_telemetry_keeps_sample_time_without_backdating_connection(client_and_database, endpoint):
    client, database = client_and_database
    before = datetime.now(timezone.utc)
    old = before - timedelta(days=1)
    response = client.post(f"/api/agents/{endpoint}", headers={"X-Agent-Api-Key": "test-key"}, json={
        "device_id": "device-1", "timestamp": old.isoformat(),
        "system": {"computer_name": "PC1"}, "cpu": {"usage_percent": 25},
    })
    assert response.status_code == 200, response.text
    assert datetime.fromisoformat(database.rows["diagnostic_readings"][0]["recorded_at"]) == old
    assert datetime.fromisoformat(database.rows["computers"][0]["last_seen"]) >= before


def test_queued_python_reading_does_not_backdate_connection(client_and_database):
    client, database = client_and_database
    before = datetime.now(timezone.utc)
    old = before - timedelta(days=1)
    response = client.post("/api/readings", headers={"X-Agent-Api-Key": "test-key"}, json={
        "device_id": "device-1", "recorded_at": old.isoformat(), "cpu_usage": 25,
    })
    assert response.status_code == 200, response.text
    assert datetime.fromisoformat(database.rows["diagnostic_readings"][0]["recorded_at"]) == old
    row = database.rows["computers"][0]
    assert datetime.fromisoformat(row["last_seen"]) >= before
    assert row["last_heartbeat"] == row["last_seen"]


def test_offline_sweep_does_not_overwrite_new_heartbeat(monkeypatch):
    database = MemoryDatabase()
    monkeypatch.setattr(offline, "load_thresholds", lambda client: Thresholds())
    fresh = datetime.now(timezone.utc).isoformat()

    def heartbeat_arrives():
        database.rows["computers"][0]["last_seen"] = fresh
        database.before_update = None

    database.before_update = heartbeat_arrives
    assert offline.mark_stale_computers(database) == 1
    assert database.rows["computers"][0]["status"] == "warning"
    assert database.rows["computers"][1]["status"] == "offline"


def test_offline_sweep_marks_device_without_heartbeat(monkeypatch):
    database = MemoryDatabase()
    database.rows["computers"][0]["last_seen"] = None
    monkeypatch.setattr(offline, "load_thresholds", lambda client: Thresholds())
    assert offline.mark_stale_computers(database) == 2
