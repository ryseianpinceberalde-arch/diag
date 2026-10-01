import hashlib
import sqlite3
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from config import Settings, get_settings
from dependencies import admin_client
from routers.agents import router
from schemas.models import AgentRegistration


class RegistrationDatabase:
    """Exercise registration writes against SQL defaults and NOT NULL constraints."""

    def __init__(self):
        self.connection = sqlite3.connect(":memory:", check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        optional_columns = [
            f'"{name}" text'
            for name in AgentRegistration.model_fields
            if name not in {"device_id", "computer_name", "device_type", "registration_code"}
        ]
        # These required fields/defaults match the computers migrations.
        self.connection.execute(
            "create table computers ("
            "id text default 'computer-id', device_id text not null unique, "
            "computer_name text not null, device_type text not null default 'computer', "
            "status text, agent_status text, last_seen text, agent_token_hash text, "
            + ", ".join(optional_columns) + ")"
        )

    def table(self, name):
        assert name == "computers"
        return self

    def upsert(self, row, on_conflict):
        assert on_conflict == "device_id"
        self.pending_row = row
        return self

    def execute(self):
        columns = list(self.pending_row)
        names = ", ".join(f'"{name}"' for name in columns)
        placeholders = ", ".join("?" for _ in columns)
        updates = ", ".join(f'"{name}" = excluded."{name}"' for name in columns)
        row = self.connection.execute(
            f"insert into computers ({names}) values ({placeholders}) "
            f"on conflict (device_id) do update set {updates} returning *",
            list(self.pending_row.values()),
        ).fetchone()
        return SimpleNamespace(data=[dict(row)])


@pytest.fixture
def registration_client():
    database = RegistrationDatabase()
    settings = Settings(
        _env_file=None,
        SUPABASE_URL="https://example.supabase.co",
        SUPABASE_ANON_KEY="test-anon",
        SUPABASE_SERVICE_ROLE_KEY="test-service",
        AGENT_API_KEY="test-agent-key",
    )
    app = FastAPI()
    app.include_router(router, prefix="/api/agents")
    app.include_router(router, prefix="/api/agent")
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[admin_client] = lambda: database
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client, database
    finally:
        database.connection.close()


def register(client, path="/api/agents/register", **metadata):
    return client.post(
        path,
        headers={"X-Agent-Api-Key": "test-agent-key"},
        json={
            "device_id": "test-device-123",
            "computer_name": "OFFICE-PC",
            "manufacturer": None,
            "model": None,
            "operating_system": "Windows 11",
            "ip_address": "192.0.2.10",
            "agent_version": "0.2.0",
            **metadata,
        },
    )


@pytest.mark.parametrize("path", ["/api/agents/register", "/api/agent/register"])
@pytest.mark.parametrize("metadata", [{}, {"device_type": None}])
def test_registration_uses_database_default_for_missing_device_type(registration_client, path, metadata):
    client, _ = registration_client
    response = register(client, path, **metadata)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["computer"]["device_type"] == "computer"
    assert body["computer"]["ip_address"] == "192.0.2.10"
    assert body["computer"]["agent_status"] == "online"
    assert body["computer"]["agent_token_hash"] == hashlib.sha256(body["token"].encode()).hexdigest()


def test_repeat_registration_preserves_asset_details_missing_from_agent(registration_client):
    client, _ = registration_client
    original = {"device_type": "laptop", "asset_tag": "ASSET-123", "owner_name": "Test Owner"}
    assert register(client, **original).status_code == 200

    response = register(client, computer_name="RENAMED-PC", owner_name=None)

    assert response.status_code == 200, response.text
    computer = response.json()["computer"]
    assert computer["computer_name"] == "RENAMED-PC"
    for name, value in original.items():
        assert computer[name] == value


def test_registration_accepts_explicit_device_type(registration_client):
    client, _ = registration_client
    response = register(client, device_type="laptop")

    assert response.status_code == 200, response.text
    assert response.json()["computer"]["device_type"] == "laptop"


def test_registration_still_requires_credentials(registration_client):
    client, database = registration_client
    response = client.post(
        "/api/agents/register",
        json={"device_id": "test-device-123", "computer_name": "OFFICE-PC"},
    )

    assert response.status_code == 422
    assert database.connection.execute("select count(*) from computers").fetchone()[0] == 0
