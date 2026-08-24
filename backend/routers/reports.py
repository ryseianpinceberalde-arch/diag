from datetime import datetime
from fastapi import APIRouter, Depends
from supabase import Client
from dependencies import admin_client, require_admin

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(require_admin)])


@router.get("/maintenance")
def maintenance_report(
    computer_id: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    client: Client = Depends(admin_client),
) -> dict:
    query = client.table("maintenance_tickets").select("*, computers(computer_name, device_id)").order("created_at", desc=True).limit(200)
    if computer_id:
        query = query.eq("computer_id", computer_id)
    if start:
        query = query.gte("created_at", start.isoformat())
    if end:
        query = query.lte("created_at", end.isoformat())
    tickets = query.execute().data or []
    if tickets:
        return {
            "items": [
                {
                    "id": row.get("id"),
                    "computer": row.get("computers"),
                    "risk_level": row.get("priority"),
                    "risk_score": None,
                    "component": row.get("component"),
                    "recommendation": row.get("description"),
                    "status": row.get("status"),
                    "assigned_technician": row.get("assigned_technician"),
                    "due_date": row.get("due_date"),
                    "created_at": row.get("created_at"),
                }
                for row in tickets
            ]
        }

    predictions = client.table("predictions").select("*, computers(computer_name, device_id)").order("created_at", desc=True).limit(100).execute().data or []
    seen = set()
    items = []
    for row in predictions:
        key = (row.get("computer_id"), row.get("suspected_component"), row.get("recommended_action"))
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "computer": row.get("computers"),
                "risk_level": row.get("risk_level"),
                "risk_score": row.get("risk_score"),
                "component": row.get("suspected_component"),
                "recommendation": row.get("recommended_action"),
                "created_at": row.get("created_at"),
            }
        )
    return {
        "items": items
    }
