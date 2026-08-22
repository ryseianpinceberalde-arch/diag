from datetime import datetime
from fastapi import APIRouter, Depends, Query
from supabase import Client
from dependencies import admin_client, require_admin
from services.prediction import analyze_computer
from services.status import effective_status, health_from_prediction

router = APIRouter(prefix="/computers", tags=["computers"], dependencies=[Depends(require_admin)])


@router.get("")
def list_computers(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    client: Client = Depends(admin_client),
) -> dict:
    computers = client.table("computers").select("*", count="exact").order("last_seen", desc=True).range(offset, offset + limit - 1).execute()
    items = computers.data or []
    for item in items:
        latest = client.table("diagnostic_readings").select("*").eq("computer_id", item["id"]).order("recorded_at", desc=True).limit(1).execute().data
        prediction = client.table("predictions").select("*").eq("computer_id", item["id"]).order("created_at", desc=True).limit(1).execute().data
        item["status"] = effective_status(item)
        item["latest_reading"] = latest[0] if latest else None
        item["latest_prediction"] = prediction[0] if prediction else None
        item["health_level"] = health_from_prediction(item["latest_prediction"], item["status"])
    return {"items": items, "total": computers.count or len(items), "limit": limit, "offset": offset}


@router.get("/{computer_id}")
def get_computer(computer_id: str, client: Client = Depends(admin_client)) -> dict:
    computer = client.table("computers").select("*").eq("id", computer_id).single().execute().data
    latest = client.table("diagnostic_readings").select("*").eq("computer_id", computer_id).order("recorded_at", desc=True).limit(1).execute().data
    alerts = client.table("alerts").select("*").eq("computer_id", computer_id).order("created_at", desc=True).limit(50).execute().data or []
    prediction = client.table("predictions").select("*").eq("computer_id", computer_id).order("created_at", desc=True).limit(1).execute().data
    computer["status"] = effective_status(computer)
    latest_prediction = prediction[0] if prediction else None
    computer["health_level"] = health_from_prediction(latest_prediction, computer["status"])
    return {
        "computer": computer,
        "latest_reading": latest[0] if latest else None,
        "alerts": alerts,
        "latest_prediction": latest_prediction,
    }


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


@router.get("/{computer_id}/predictions")
def get_predictions(computer_id: str, client: Client = Depends(admin_client)) -> dict:
    rows = client.table("predictions").select("*").eq("computer_id", computer_id).order("created_at", desc=True).limit(100).execute().data or []
    return {"items": rows}


@router.post("/{computer_id}/analyze")
def analyze(computer_id: str, client: Client = Depends(admin_client)) -> dict:
    return analyze_computer(client, computer_id, save=True)
