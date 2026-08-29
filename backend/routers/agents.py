import logging
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import Response
from pathlib import Path
from pydantic import BaseModel
from supabase import Client
from config import Settings, get_settings
from dependencies import admin_client, require_admin, require_agent_credential
from schemas.models import AgentHeartbeat, AgentRegistration, AgentTelemetry

router = APIRouter(tags=["agents"])
logger = logging.getLogger("pc_sentinel.agents")
AGENT_SCRIPT = Path(__file__).resolve().parents[2] / "agents" / "windows" / "pc-monitoring-agent.ps1"
AGENT_LATEST_VERSION = "1.1.0"


class CommandComplete(BaseModel):
    status: str
    result: dict | None = None
    error: str | None = None


@router.post("/registration-codes", dependencies=[Depends(require_admin)])
def create_registration_code(user: dict = Depends(require_admin), client: Client = Depends(admin_client)) -> dict:
    code = secrets.token_urlsafe(12)
    row = {"code_hash": hashlib.sha256(code.encode("utf-8")).hexdigest(), "status": "active", "created_by": user["id"], "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()}
    result = client.table("registration_codes").insert(row).execute().data
    return {"code": code, "registration_code": result[0] if result else row}


@router.get("/download/powershell", dependencies=[Depends(require_admin)])
def download_powershell_agent(
    api_base_url: str = Query(..., min_length=8),
    registration_code: str = Query(default=""),
    interval_seconds: int = Query(default=10, ge=10, le=3600),
) -> Response:
    if not AGENT_SCRIPT.exists():
        raise HTTPException(status_code=500, detail="PowerShell agent is not installed")
    if not api_base_url.lower().startswith("https://"):
        raise HTTPException(status_code=422, detail="api_base_url must use HTTPS")
    script = AGENT_SCRIPT.read_text(encoding="utf-8")
    script = script.replace('[string]$ApiBaseUrl = $env:PC_MONITORING_API_URL,', f'[string]$ApiBaseUrl = "{api_base_url.replace(chr(34), chr(34) * 2)}",')
    script = script.replace('  [string]$RegistrationCode,', f'  [string]$RegistrationCode = "{registration_code.replace(chr(34), chr(34) * 2)}",')
    script = script.replace('  [int]$IntervalSeconds = 10,', f'  [int]$IntervalSeconds = {interval_seconds},')
    return Response(content=script, media_type="text/plain", headers={"Content-Disposition": 'attachment; filename="pc-monitoring-agent.ps1"', "Cache-Control": "no-store"})


@router.post("/register")
def register_agent(
    payload: AgentRegistration,
    x_agent_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    client: Client = Depends(admin_client),
) -> dict:
    code_row = None
    if not (x_agent_api_key and x_agent_api_key == settings.agent_api_key):
        if not payload.registration_code:
            raise HTTPException(status_code=422, detail="registration_code is required")
        code_hash = hashlib.sha256(payload.registration_code.encode("utf-8")).hexdigest()
        codes = client.table("registration_codes").select("id,expires_at,status,device_id").eq("code_hash", code_hash).eq("status", "active").limit(1).execute().data or []
        if not codes:
            raise HTTPException(status_code=401, detail="Invalid or expired registration code")
        expires_at = codes[0].get("expires_at")
        if expires_at and datetime.fromisoformat(expires_at.replace("Z", "+00:00")) <= datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Invalid or expired registration code")
        if codes[0].get("device_id") and codes[0]["device_id"] != payload.device_id:
            raise HTTPException(status_code=401, detail="Registration code is assigned to another device")
        code_row = codes[0]
    token = secrets.token_urlsafe(32)
    row = payload.model_dump(mode="json")
    row.pop("registration_code", None)
    row["status"] = "online"
    row["agent_status"] = "online"
    row["last_seen"] = datetime.now(timezone.utc).isoformat()
    row["agent_token_hash"] = hashlib.sha256(token.encode("utf-8")).hexdigest()
    result = client.table("computers").upsert(row, on_conflict="device_id").execute().data
    computer = result[0] if result else row
    if code_row:
        client.table("registration_codes").update({"status": "used", "used_at": row["last_seen"]}).eq("id", code_row["id"]).execute()
    logger.info("Agent registration successful device_id=%s computer=%s", payload.device_id, payload.computer_name)
    return {
        "success": True,
        "computer": computer,
        "computer_id": computer.get("id"),
        "device_id": payload.device_id,
        "deviceId": payload.device_id,
        "token": token,
        "deviceToken": token,
        "heartbeat_interval": settings.agent_heartbeat_interval_seconds,
        "heartbeatIntervalSec": settings.agent_heartbeat_interval_seconds,
    }


def _ingest_telemetry(
    payload: AgentTelemetry,
    authorization: str | None = Header(default=None),
    client: Client = Depends(admin_client),
) -> dict:
    computers = client.table("computers").select("id").eq("device_id", payload.device_id).limit(1).execute().data or []
    if not computers:
        raise HTTPException(status_code=404, detail="Computer is not registered")
    if authorization and authorization.lower().startswith("bearer "):
        token_hash = hashlib.sha256(authorization.split(" ", 1)[1].strip().encode("utf-8")).hexdigest()
        owned = client.table("computers").select("id").eq("id", computers[0]["id"]).eq("agent_token_hash", token_hash).limit(1).execute().data or []
        if not owned:
            raise HTTPException(status_code=403, detail="Credential does not belong to this device")
    now = (payload.last_heartbeat or payload.timestamp or datetime.now(timezone.utc)).isoformat()
    system, cpu, memory = payload.system, payload.cpu, payload.memory
    connected_network = next(
        (
            item
            for item in payload.network
            if str(item.get("status") or "").lower() in {"up", "connected"} and item.get("ipv4")
        ),
        payload.network[0] if payload.network else {},
    )
    disk_health = next(
        (
            item.get("smart_status") or item.get("health")
            for item in payload.storage
            if str(item.get("smart_status") or item.get("health") or "").lower()
            in {"warning", "unhealthy", "bad", "fail", "failed", "critical"}
        ),
        next((item.get("smart_status") or item.get("health") for item in payload.storage if item.get("smart_status") or item.get("health")), None),
    )
    temperature = payload.temperature or {}
    row = {
        "computer_id": computers[0]["id"], "cpu_usage": cpu.get("usage_percent"),
        "ram_usage": memory.get("usage_percent"),
        "disk_usage": max((item.get("usage_percent") for item in payload.storage if item.get("usage_percent") is not None), default=None),
        "disk_health": disk_health,
        "battery_percentage": (payload.battery or {}).get("percentage"),
        "battery_health": (payload.battery or {}).get("health_percent"),
        "network_latency": connected_network.get("latency_ms"),
        "packet_loss": connected_network.get("packet_loss_percent"),
        "uptime_seconds": system.get("uptime_seconds"),
        "cpu_temperature": temperature.get("temperatureC") if temperature.get("available") else None,
        "recorded_at": now,
    }
    inserted = client.table("diagnostic_readings").insert(row).execute().data
    client.table("computers").update({
        "status": "online", "agent_status": "online", "last_seen": now, "last_heartbeat": now,
        "agent_version": payload.agent_version, "capabilities": payload.capabilities or ["cpu", "memory", "storage", "network"],
        "computer_name": system.get("computer_name"), "manufacturer": system.get("manufacturer"),
        "model": system.get("model"), "operating_system": system.get("windows_version"),
        "ip_address": connected_network.get("ipv4"),
        "serial_number": system.get("serial_number"), "windows_build": system.get("windows_build"),
        "architecture": system.get("architecture"), "agent_inventory": payload.model_dump(mode="json"),
        **({"device_type": system.get("device_type")} if system.get("device_type") else {}),
    }).eq("id", computers[0]["id"]).execute()
    return {"success": True, "last_heartbeat": now, "reading": inserted[0] if inserted else row}


@router.post("/heartbeat", dependencies=[Depends(require_agent_credential)])
def heartbeat(payload: AgentHeartbeat, authorization: str | None = Header(default=None), client: Client = Depends(admin_client)) -> dict:
    return _ingest_telemetry(payload, authorization, client)


@router.post("/telemetry", dependencies=[Depends(require_agent_credential)])
def telemetry(payload: AgentTelemetry, authorization: str | None = Header(default=None), client: Client = Depends(admin_client)) -> dict:
    return _ingest_telemetry(payload, authorization, client)


@router.get("/version")
def agent_version() -> dict[str, str]:
    return {"latestVersion": AGENT_LATEST_VERSION, "minimumSupportedVersion": "1.0.0"}


@router.post("/{computer_id}/regenerate-token", dependencies=[Depends(require_admin)])
def regenerate_token(computer_id: str, client: Client = Depends(admin_client)) -> dict:
    token = secrets.token_urlsafe(32)
    result = client.table("computers").update({"agent_token_hash": hashlib.sha256(token.encode("utf-8")).hexdigest()}).eq("id", computer_id).execute().data
    if not result:
        raise HTTPException(status_code=404, detail="Computer not found")
    return {"token": token, "computer_id": computer_id}


@router.get("/commands/pending", dependencies=[Depends(require_agent_credential)])
def pending_commands(device_id: str, client: Client = Depends(admin_client)) -> dict:
    computer = client.table("computers").select("id").eq("device_id", device_id).limit(1).execute().data or []
    if not computer:
        raise HTTPException(status_code=404, detail="Computer is not registered")
    try:
        rows = (
            client.table("agent_commands")
            .select("*")
            .eq("device_id", device_id)
            .eq("status", "queued")
            .order("requested_at", desc=False)
            .limit(3)
            .execute()
            .data
            or []
        )
    except Exception:
        logger.exception("Could not load pending commands for device_id=%s", device_id)
        return {"items": []}
    now = datetime.now(timezone.utc).isoformat()
    for row in rows:
        client.table("agent_commands").update({"status": "running", "picked_up_at": now}).eq("id", row["id"]).eq("status", "queued").execute()
        row["status"] = "running"
        row["picked_up_at"] = now
    return {"items": rows}


@router.post("/commands/{command_id}/complete", dependencies=[Depends(require_agent_credential)])
def complete_command(command_id: str, payload: CommandComplete, client: Client = Depends(admin_client)) -> dict:
    if payload.status not in {"completed", "failed"}:
        raise HTTPException(status_code=422, detail="Command status must be completed or failed")
    row = {
        "status": payload.status,
        "result": payload.result or {},
        "error": payload.error,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    result = client.table("agent_commands").update(row).eq("id", command_id).execute().data
    return {"command": result[0] if result else row}


@router.get("", dependencies=[Depends(require_admin)])
def list_agents(client: Client = Depends(admin_client)) -> dict:
    rows = client.table("computers").select("*").order("last_seen", desc=True).execute().data or []
    return {"items": rows, "total": len(rows)}


def _agent_by_device(device_id: str, client: Client) -> dict:
    rows = client.table("computers").select("*").eq("device_id", device_id).limit(1).execute().data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Agent not found")
    return rows[0]


@router.get("/{device_id}", dependencies=[Depends(require_admin)])
def get_agent(device_id: str, client: Client = Depends(admin_client)) -> dict:
    computer = _agent_by_device(device_id, client)
    readings = client.table("diagnostic_readings").select("*").eq("computer_id", computer["id"]).order("recorded_at", desc=True).limit(1).execute().data or []
    return {"agent": computer, "latest_reading": readings[0] if readings else None}


@router.get("/{device_id}/metrics", dependencies=[Depends(require_admin)])
def agent_metrics(device_id: str, client: Client = Depends(admin_client)) -> dict:
    computer = _agent_by_device(device_id, client)
    rows = client.table("diagnostic_readings").select("*").eq("computer_id", computer["id"]).order("recorded_at", desc=True).limit(200).execute().data or []
    return {"items": rows}


@router.get("/{device_id}/history", dependencies=[Depends(require_admin)])
def agent_history(device_id: str, client: Client = Depends(admin_client)) -> dict:
    return agent_metrics(device_id, client)


@router.get("/{device_id}/processes", dependencies=[Depends(require_admin)])
def agent_processes(device_id: str, client: Client = Depends(admin_client)) -> dict:
    return {"items": (_agent_by_device(device_id, client).get("agent_inventory") or {}).get("processes", [])}


@router.get("/{device_id}/hardware", dependencies=[Depends(require_admin)])
def agent_hardware(device_id: str, client: Client = Depends(admin_client)) -> dict:
    inventory = _agent_by_device(device_id, client).get("agent_inventory") or {}
    return {"cpu": inventory.get("cpu", {}), "memory": inventory.get("memory", {}), "storage": inventory.get("storage", []), "gpu": inventory.get("gpu", []), "battery": inventory.get("battery"), "health": inventory.get("hardware_health", {})}


@router.get("/{device_id}/network", dependencies=[Depends(require_admin)])
def agent_network(device_id: str, client: Client = Depends(admin_client)) -> dict:
    return {"items": ((_agent_by_device(device_id, client).get("agent_inventory") or {}).get("network", []))}


@router.get("/{device_id}/alerts", dependencies=[Depends(require_admin)])
def agent_alerts(device_id: str, client: Client = Depends(admin_client)) -> dict:
    computer = _agent_by_device(device_id, client)
    rows = client.table("alerts").select("*").eq("computer_id", computer["id"]).order("created_at", desc=True).limit(100).execute().data or []
    return {"items": rows}
