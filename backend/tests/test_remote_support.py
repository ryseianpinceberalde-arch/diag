from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from database import get_supabase_admin, get_supabase_anon
from dependencies import admin_client
from routers import computers


class Query:
    def __init__(self, database, table):
        self.database, self.table = database, table
        self.filters, self.operation, self.value = [], "select", None

    def select(self, *_):
        return self

    def limit(self, *_):
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def upsert(self, value, on_conflict):
        assert on_conflict == "key"
        self.operation, self.value = "upsert", value
        return self

    def insert(self, value):
        self.operation, self.value = "insert", value
        return self

    def execute(self):
        rows = self.database.rows[self.table]
        if self.operation == "upsert":
            rows[:] = [row for row in rows if row["key"] != self.value["key"]]
        if self.operation in {"insert", "upsert"}:
            rows.append(deepcopy(self.value))
        return SimpleNamespace(data=deepcopy([row for row in rows if all(row.get(k) == v for k, v in self.filters)]))


class Database:
    def __init__(self):
        self.rows = {
            "computers": [{"id": "pc-1", "status": "offline"}, {"id": "pc-2", "status": "online"}],
            "profiles": [{"id": "admin", "role": "administrator"}],
            "app_settings": [], "audit_logs": [],
        }

    def table(self, name):
        return Query(self, name)


@pytest.fixture
def setup():
    database = Database()
    anon = SimpleNamespace(auth=SimpleNamespace(get_user=lambda _: SimpleNamespace(user=SimpleNamespace(id="admin", email="admin@example.test"))))
    app = FastAPI()
    app.include_router(computers.router, prefix="/api/computers")
    app.dependency_overrides[admin_client] = lambda: database
    app.dependency_overrides[get_supabase_admin] = lambda: database
    app.dependency_overrides[get_supabase_anon] = lambda: anon
    with TestClient(app, headers={"Authorization": "Bearer test-user-token"}) as client:
        yield client, database


BASE = "/api/computers/pc-1/remote-support"


def test_config_and_launch_are_per_computer_and_audited(setup):
    client, database = setup
    assert client.get(BASE).json() == {"enabled": False, "rustdesk_id": ""}
    assert client.post(BASE + "/launch", json={"mode": "desktop"}).status_code == 409
    response = client.put(BASE, json={"enabled": True, "rustdesk_id": "123 456 789"})
    assert response.status_code == 200
    assert response.json() == {"enabled": True, "rustdesk_id": "123456789"}
    second = BASE.replace("pc-1", "pc-2")
    assert client.get(second).json()["enabled"] is False
    assert client.put(second, json={"enabled": True, "rustdesk_id": "987654321"}).status_code == 200
    for mode, command in (("desktop", "connect"), ("file_transfer", "file-transfer")):
        response = client.post(BASE + "/launch", json={"mode": mode})
        assert response.status_code == 200
        assert response.json()["uri"] == f"rustdesk://{command}/123456789"
    assert client.post(second + "/launch", json={"mode": "desktop"}).json()["uri"] == "rustdesk://connect/987654321"
    assert client.get(BASE).json()["rustdesk_id"] == "123456789"
    assert len(database.rows["audit_logs"]) == 5
    assert database.rows["audit_logs"][-1]["action"] == "remote_support.launch_requested"
    assert database.rows["audit_logs"][-1]["actor_id"] == "admin"
    assert all("password" not in str(row).lower() for row in database.rows["app_settings"])


@pytest.mark.parametrize("role", ["technician", "viewer"])
def test_non_admin_cannot_read_configure_or_launch(setup, role):
    client, database = setup
    database.rows["profiles"][0]["role"] = role
    assert client.get(BASE).status_code == 403
    assert client.put(BASE, json={"enabled": True, "rustdesk_id": "123456789"}).status_code == 403
    assert client.post(BASE + "/launch", json={"mode": "desktop"}).status_code == 403
    assert not database.rows["app_settings"]
    assert not database.rows["audit_logs"]


def test_authentication_and_existing_computer_required(setup):
    client, database = setup
    client.headers.clear()
    assert client.get(BASE).status_code == 401
    assert client.put(BASE, json={}).status_code == 401
    assert client.post(BASE + "/launch", json={"mode": "desktop"}).status_code == 401
    client.headers["Authorization"] = "Bearer test"
    missing = BASE.replace("pc-1", "missing")
    assert client.get(missing).status_code == 404
    assert client.put(missing, json={}).status_code == 404
    assert client.post(missing + "/launch", json={"mode": "desktop"}).status_code == 404
    assert not database.rows["app_settings"]


@pytest.mark.parametrize("rustdesk_id", ["", "123", "1" * 17, "123456789?password=secret", "rustdesk://config/host", "１２３４５６７８９", "123456/../config"])
def test_rejects_invalid_ids_without_writing(setup, rustdesk_id):
    client, database = setup
    assert client.put(BASE, json={"enabled": True, "rustdesk_id": rustdesk_id}).status_code == 422
    assert not database.rows["app_settings"]
    assert not database.rows["audit_logs"]


def test_disabled_config_and_arbitrary_launch_mode_rejected(setup):
    client, database = setup
    client.put(BASE, json={"enabled": True, "rustdesk_id": "123456789"})
    assert client.post(BASE + "/launch", json={"mode": "terminal"}).status_code == 422
    client.put(BASE, json={"enabled": False, "rustdesk_id": "123456789"})
    assert client.post(BASE + "/launch", json={"mode": "desktop"}).status_code == 409
    assert len(database.rows["audit_logs"]) == 2
