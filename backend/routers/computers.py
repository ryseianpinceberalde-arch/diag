from datetime import date, datetime, timedelta, timezone
from uuid import uuid4
import hashlib
import secrets
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from supabase import Client
from dependencies import admin_client, require_admin, require_role
from services.prediction import analyze_computer
from services.health import evaluate_computer_health
from services.settings import load_thresholds
from services.status import effective_status
from services.health_score import calculate_health_score

router = APIRouter(tags=["computers"], dependencies=[Depends(require_admin)])

COMMAND_ACTIONS = {
    "system_info",
    "process_list",
    "services_list",
    "disk_summary",
    "network_test",
    "restart",
    "shutdown",
    "uninstall_agent",
}


class ComputerUpdate(BaseModel):
    display_name: str | None = None
    asset_tag: str | None = None
    device_type: str | None = None
    department_id: str | None = None
    location_id: str | None = None
    assigned_user_id: str | None = None
    owner_name: str | None = None
    purchase_date: date | None = None
    warranty_start_date: date | None = None
    warranty_end_date: date | None = None
    tags: list[str] | None = None
    notes: str | None = None


class ComputerCreate(ComputerUpdate):
    device_id: str | None = None
    computer_name: str = Field(min_length=1, max_length=200)
    manufacturer: str | None = None
    model: str | None = None
    operating_system: str | None = None
    os_version: str | None = None
    architecture: str | None = None


class CommandCreate(BaseModel):
    action: str = Field(min_length=1, max_length=80)


@router.get("")
def list_computers(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: str | None = None,
    department_id: str | None = None,
    location_id: str | None = None,
    device_type: str | None = None,
    agent_status: str | None = None,
    search: str | None = None,
    client: Client = Depends(admin_client),
) -> dict:
    thresholds = load_thresholds(client)
    computers = client.table("computers").select("*", count="exact").order("last_seen", desc=True).range(offset, offset + limit - 1).execute()
    items = computers.data or []
    if status:
        items = [item for item in items if item.get("status") == status]
    if department_id:
        items = [item for item in items if item.get("department_id") == department_id]
    if location_id:
        items = [item for item in items if item.get("location_id") == location_id]
    if device_type:
        items = [item for item in items if item.get("device_type") == device_type]
    if agent_status:
        items = [item for item in items if item.get("agent_status") == agent_status]
    if search:
        needle = search.lower()
        items = [item for item in items if any(needle in str(item.get(key) or "").lower() for key in ("computer_name", "asset_tag", "serial_number", "model", "owner_name"))]
    for item in items:
        latest = client.table("diagnostic_readings").select("*").eq("computer_id", item["id"]).order("recorded_at", desc=True).limit(1).execute().data
        prediction = client.table("predictions").select("*").eq("computer_id", item["id"]).order("created_at", desc=True).limit(1).execute().data
        health = evaluate_computer_health(item, latest[0] if latest else None, thresholds)
        item["status"] = effective_status(item, offline_after_seconds=thresholds.offline_after_seconds)
        item["latest_reading"] = latest[0] if latest else None
        item["latest_prediction"] = prediction[0] if prediction else None
        item["health_level"] = health["status"]
        item["health_issues"] = health["issues"]
        item["health_score"] = calculate_health_score(latest[0] if latest else None, item.get("agent_inventory"))
    return {"items": items, "total": computers.count or len(items), "limit": limit, "offset": offset}


@router.post("", dependencies=[Depends(require_role("administrator", "technician"))])
def create_computer(payload: ComputerCreate, user: dict = Depends(require_role("administrator", "technician")), client: Client = Depends(admin_client)) -> dict:
    row = payload.model_dump(mode="json", exclude_none=True)
    row["device_id"] = row.get("device_id") or f"pending-{uuid4()}"
    row["display_name"] = row.get("display_name") or row["computer_name"]
    row["status"] = "offline"
    row["agent_status"] = "waiting_for_agent"
    result = client.table("computers").insert(row).execute().data or []
    created = result[0] if result else row
    client.table("audit_logs").insert({"actor_id": user["id"], "action": "device.created", "target_type": "computer", "target_id": created.get("id"), "metadata": {"device_id": row["device_id"]}}).execute()
    return {"computer": created}


@router.post("/{computer_id}/registration-code", dependencies=[Depends(require_role("administrator"))])
def create_device_registration_code(computer_id: str, user: dict = Depends(require_role("administrator")), client: Client = Depends(admin_client)) -> dict:
    computer = client.table("computers").select("id").eq("id", computer_id).limit(1).execute().data or []
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")
    code = secrets.token_urlsafe(12)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    row = {"code_hash": hashlib.sha256(code.encode()).hexdigest(), "device_id": computer_id, "created_by": user["id"], "expires_at": expires_at.isoformat(), "status": "active"}
    client.table("registration_codes").insert(row).execute()
    return {"code": code, "expires_at": expires_at.isoformat(), "computer_id": computer_id}


def _load_computer_detail(computer_id: str, client: Client) -> dict:
    thresholds = load_thresholds(client)
    computers = client.table("computers").select("*").eq("id", computer_id).limit(1).execute().data or []
    if not computers:
        raise HTTPException(status_code=404, detail="Computer not found")
    computer = computers[0]
    latest = client.table("diagnostic_readings").select("*").eq("computer_id", computer_id).order("recorded_at", desc=True).limit(1).execute().data
    alerts = client.table("alerts").select("*").eq("computer_id", computer_id).order("created_at", desc=True).limit(50).execute().data or []
    prediction = client.table("predictions").select("*").eq("computer_id", computer_id).order("created_at", desc=True).limit(1).execute().data
    health = evaluate_computer_health(computer, latest[0] if latest else None, thresholds)
    computer["status"] = effective_status(computer, offline_after_seconds=thresholds.offline_after_seconds)
    latest_prediction = prediction[0] if prediction else None
    computer["health_level"] = health["status"]
    computer["health_issues"] = health["issues"]
    computer["health_score"] = calculate_health_score(latest[0] if latest else None, computer.get("agent_inventory"))
    assigned_user = None
    if computer.get("assigned_user_id"):
        profiles = client.table("profiles").select("id,full_name").eq("id", computer["assigned_user_id"]).limit(1).execute().data or []
        assigned_user = profiles[0] if profiles else None
    return {
        "computer": computer,
        "latest_reading": latest[0] if latest else None,
        "alerts": alerts,
        "latest_prediction": latest_prediction,
        "assigned_user": assigned_user,
    }


def _load_agent_inventory(computer_id: str, client: Client) -> dict:
    rows = client.table("computers").select("agent_inventory").eq("id", computer_id).limit(1).execute().data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Computer not found")
    return rows[0].get("agent_inventory") or {}


@router.get("/{computer_id}")
def get_computer(
    computer_id: str,
    user: dict = Depends(require_admin),
    client: Client = Depends(admin_client),
) -> dict:
    detail = _load_computer_detail(computer_id, client)
    is_administrator = user["role"] == "administrator"
    can_service = user["role"] in {"administrator", "technician"}
    detail["permissions"] = {
        "update_agent": is_administrator,
        "remote_support": is_administrator,
        "log_maintenance": can_service,
        "create_ticket": can_service,
        "delete_device": is_administrator,
        "edit_device": can_service,
        "run_analysis": can_service,
        "download_report": True,
    }
    return detail


@router.get("/{computer_id}/health")
def get_health(computer_id: str, client: Client = Depends(admin_client)) -> dict:
    detail = _load_computer_detail(computer_id, client)
    return calculate_health_score(detail["latest_reading"], detail["computer"].get("agent_inventory"))


@router.patch("/{computer_id}", dependencies=[Depends(require_role("administrator", "technician"))])
def update_computer(computer_id: str, payload: ComputerUpdate, user: dict = Depends(require_role("administrator", "technician")), client: Client = Depends(admin_client)) -> dict:
    row = payload.model_dump(exclude_none=True, mode="json")
    if "tags" in row:
        row["tags"] = [tag.strip() for tag in row["tags"] if tag.strip()][:12]
    result = client.table("computers").update(row).eq("id", computer_id).execute().data
    client.table("audit_logs").insert({"actor_id": user["id"], "action": "computer.update", "target_type": "computer", "target_id": computer_id, "metadata": row}).execute()
    return {"computer": result[0] if result else None}


@router.delete("/{computer_id}", dependencies=[Depends(require_role("administrator"))])
def delete_computer(
    computer_id: str,
    user: dict = Depends(require_role("administrator")),
    client: Client = Depends(admin_client),
) -> dict:
    computer = client.table("computers").select("id,computer_name,device_id").eq("id", computer_id).limit(1).execute().data or []
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")
    client.table("audit_logs").insert(
        {
            "actor_id": user["id"],
            "action": "device.delete",
            "target_type": "computer",
            "target_id": computer_id,
            "metadata": {"computer_name": computer[0].get("computer_name"), "device_id": computer[0].get("device_id")},
        }
    ).execute()
    client.table("computers").delete().eq("id", computer_id).execute()
    return {"deleted": True, "computer_id": computer_id}


@router.get("/{computer_id}/history")
def get_history(
    computer_id: str,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
    client: Client = Depends(admin_client),
) -> dict:
    query = client.table("diagnostic_readings").select("*").eq("computer_id", computer_id).order("recorded_at", desc=False).limit(limit)
    if start:
        query = query.gte("recorded_at", start.isoformat())
    if end:
        query = query.lte("recorded_at", end.isoformat())
    readings = query.execute().data or []
    events = client.table("system_events").select("*").eq("computer_id", computer_id).order("occurred_at", desc=True).limit(100).execute().data or []
    return {"readings": readings, "events": events}


@router.get("/{computer_id}/metrics")
def get_metrics(computer_id: str, client: Client = Depends(admin_client)) -> dict:
    _load_computer_detail(computer_id, client)
    rows = client.table("diagnostic_readings").select("*").eq("computer_id", computer_id).order("recorded_at", desc=True).limit(200).execute().data or []
    return {"items": rows}


@router.get("/{computer_id}/hardware")
def get_hardware(computer_id: str, client: Client = Depends(admin_client)) -> dict:
    inventory = _load_agent_inventory(computer_id, client)
    return {"system": inventory.get("system", {}), "cpu": inventory.get("cpu", {}), "memory": inventory.get("memory", {}), "storage": inventory.get("storage", []), "gpu": inventory.get("gpu", []), "battery": inventory.get("battery")}


@router.get("/{computer_id}/processes")
def get_processes(computer_id: str, client: Client = Depends(admin_client)) -> dict:
    return {"items": _load_agent_inventory(computer_id, client).get("processes", [])}


@router.get("/{computer_id}/network")
def get_network(computer_id: str, client: Client = Depends(admin_client)) -> dict:
    return {"items": _load_agent_inventory(computer_id, client).get("network", [])}


@router.get("/{computer_id}/alerts")
def get_computer_alerts(computer_id: str, client: Client = Depends(admin_client)) -> dict:
    _load_computer_detail(computer_id, client)
    rows = client.table("alerts").select("*").eq("computer_id", computer_id).order("created_at", desc=True).limit(100).execute().data or []
    return {"items": rows}


@router.get("/{computer_id}/predictions")
def get_predictions(computer_id: str, client: Client = Depends(admin_client)) -> dict:
    rows = client.table("predictions").select("*").eq("computer_id", computer_id).order("created_at", desc=True).limit(100).execute().data or []
    return {"items": rows}


@router.post("/{computer_id}/analyze", dependencies=[Depends(require_role("administrator", "technician"))])
def analyze(computer_id: str, client: Client = Depends(admin_client)) -> dict:
    return analyze_computer(client, computer_id, save=True)


@router.get("/{computer_id}/commands")
def list_commands(computer_id: str, limit: int = Query(default=25, ge=1, le=100), client: Client = Depends(admin_client)) -> dict:
    rows = client.table("agent_commands").select("*").eq("computer_id", computer_id).order("requested_at", desc=True).limit(limit).execute().data or []
    return {"items": rows}


@router.post("/{computer_id}/commands", dependencies=[Depends(require_role("administrator"))])
def create_command(computer_id: str, payload: CommandCreate, user: dict = Depends(require_role("administrator")), client: Client = Depends(admin_client)) -> dict:
    if payload.action not in COMMAND_ACTIONS:
        raise HTTPException(status_code=422, detail="Unsupported command action")
    computer = client.table("computers").select("id,device_id").eq("id", computer_id).single().execute().data
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")
    row = {
        "computer_id": computer_id,
        "device_id": computer["device_id"],
        "action": payload.action,
        "status": "queued",
        "requested_by": user["id"],
    }
    result = client.table("agent_commands").insert(row).execute().data
    client.table("audit_logs").insert({"actor_id": user["id"], "action": f"agent_command.{payload.action}", "target_type": "computer", "target_id": computer_id}).execute()
    return {"command": result[0] if result else row}


@router.get("/{computer_id}/report")
def computer_report(computer_id: str, client: Client = Depends(admin_client)) -> Response:
    detail = _load_computer_detail(computer_id, client)
    history = get_history(computer_id, limit=20, client=client)
    computer = detail["computer"]
    latest = detail["latest_reading"] or {}
    html = f"""<!doctype html>
<html>
<head><meta charset="utf-8"><title>PC Sentinel Report - {computer.get("computer_name")}</title></head>
<body>
<h1>PC Sentinel Health Report</h1>
<p><strong>Computer:</strong> {computer.get("computer_name")}</p>
<p><strong>Status:</strong> {computer.get("status")}</p>
<p><strong>Generated:</strong> {datetime.now(timezone.utc).isoformat()}</p>
<h2>Hardware</h2>
<ul>
<li>Device ID: {computer.get("device_id")}</li>
<li>OS: {computer.get("operating_system") or "-"}</li>
<li>IP: {computer.get("ip_address") or "-"}</li>
<li>Tags: {", ".join(computer.get("tags") or []) or "-"}</li>
</ul>
<h2>Latest Measurements</h2>
<ul>
<li>CPU: {latest.get("cpu_usage", "-")}%</li>
<li>RAM: {latest.get("ram_usage", "-")}%</li>
<li>Disk: {latest.get("disk_usage", "-")}%</li>
<li>CPU Temperature: {latest.get("cpu_temperature", "-")} C</li>
</ul>
<h2>Notes</h2>
<p>{computer.get("notes") or ""}</p>
<h2>Recent Readings</h2>
<p>{len(history["readings"])} readings included in dashboard history.</p>
</body>
</html>"""
    filename = f"pc-sentinel-{computer.get('computer_name', 'computer')}.html"
    return Response(content=html, media_type="text/html", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
