from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from dependencies import admin_client, require_agent_api_key
from schemas.models import DiagnosticReadingIn, SystemEventIn
from services.alerts import upsert_health_alerts, upsert_prediction_alerts

router = APIRouter(tags=["ingestion"], dependencies=[Depends(require_agent_api_key)])


def find_computer_id(client: Client, device_id: str) -> str:
    rows = client.table("computers").select("id").eq("device_id", device_id).limit(1).execute().data
    if not rows:
        raise HTTPException(status_code=404, detail="Computer is not registered")
    return rows[0]["id"]


@router.post("/readings")
def create_reading(payload: DiagnosticReadingIn, client: Client = Depends(admin_client)) -> dict:
    computer_id = find_computer_id(client, payload.device_id)
    row = payload.model_dump(exclude={"device_id"}, exclude_none=False, mode="json")
    row["computer_id"] = computer_id
    row["recorded_at"] = row["recorded_at"] or datetime.now(timezone.utc).isoformat()
    inserted = client.table("diagnostic_readings").insert(row).execute().data
    computer = client.table("computers").select("*").eq("id", computer_id).single().execute().data
    health = upsert_health_alerts(client, computer, inserted[0] if inserted else row)
    prediction = upsert_prediction_alerts(client, computer_id)
    return {"reading": inserted[0] if inserted else row, "health": health, "prediction": prediction}


@router.post("/events")
def create_event(payload: SystemEventIn, client: Client = Depends(admin_client)) -> dict:
    computer_id = find_computer_id(client, payload.device_id)
    row = payload.model_dump(exclude={"device_id"}, exclude_none=False, mode="json")
    row["computer_id"] = computer_id
    row["occurred_at"] = row["occurred_at"] or datetime.now(timezone.utc).isoformat()
    inserted = client.table("system_events").insert(row).execute().data
    return {"event": inserted[0] if inserted else row}
