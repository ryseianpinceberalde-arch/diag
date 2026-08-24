import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import Client
from dependencies import admin_client, require_agent_api_key
from schemas.models import AgentRegistration

router = APIRouter(prefix="/agents", tags=["agents"], dependencies=[Depends(require_agent_api_key)])
logger = logging.getLogger("pc_sentinel.agents")


class CommandComplete(BaseModel):
    status: str
    result: dict | None = None
    error: str | None = None


@router.post("/register")
def register_agent(payload: AgentRegistration, client: Client = Depends(admin_client)) -> dict:
    row = payload.model_dump(mode="json")
    row["status"] = "online"
    row["last_seen"] = datetime.now(timezone.utc).isoformat()
    result = client.table("computers").upsert(row, on_conflict="device_id").execute().data
    computer = result[0] if result else row
    logger.info("Agent registration successful device_id=%s computer=%s", payload.device_id, payload.computer_name)
    return {
        "success": True,
        "computer": computer,
        "computer_id": computer.get("id"),
        "device_id": payload.device_id,
        "heartbeat_interval": 60,
    }


@router.get("/commands/pending")
def pending_commands(device_id: str, client: Client = Depends(admin_client)) -> dict:
    computer = client.table("computers").select("id").eq("device_id", device_id).limit(1).execute().data or []
    if not computer:
        raise HTTPException(status_code=404, detail="Computer is not registered")
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
    now = datetime.now(timezone.utc).isoformat()
    for row in rows:
        client.table("agent_commands").update({"status": "running", "picked_up_at": now}).eq("id", row["id"]).eq("status", "queued").execute()
        row["status"] = "running"
        row["picked_up_at"] = now
    return {"items": rows}


@router.post("/commands/{command_id}/complete")
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
