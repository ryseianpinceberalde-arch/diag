from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from supabase import Client
from dependencies import admin_client, require_agent_api_key
from schemas.models import AgentRegistration

router = APIRouter(prefix="/agents", tags=["agents"], dependencies=[Depends(require_agent_api_key)])


@router.post("/register")
def register_agent(payload: AgentRegistration, client: Client = Depends(admin_client)) -> dict:
    row = payload.model_dump(mode="json")
    row["status"] = "online"
    row["last_seen"] = datetime.now(timezone.utc).isoformat()
    result = client.table("computers").upsert(row, on_conflict="device_id").execute().data
    return {"computer": result[0] if result else row}
