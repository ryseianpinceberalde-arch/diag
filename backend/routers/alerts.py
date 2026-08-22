from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from supabase import Client
from dependencies import admin_client, require_admin

router = APIRouter(prefix="/alerts", tags=["alerts"], dependencies=[Depends(require_admin)])


@router.get("")
def list_alerts(
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    client: Client = Depends(admin_client),
) -> dict:
    query = client.table("alerts").select("*, computers(computer_name, device_id)", count="exact").order("created_at", desc=True)
    if status:
        query = query.eq("status", status)
    result = query.range(offset, offset + limit - 1).execute()
    return {"items": result.data or [], "total": result.count or 0, "limit": limit, "offset": offset}


@router.patch("/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, client: Client = Depends(admin_client)) -> dict:
    row = {"status": "acknowledged", "acknowledged_at": datetime.now(timezone.utc).isoformat()}
    result = client.table("alerts").update(row).eq("id", alert_id).neq("status", "resolved").execute().data
    return {"alert": result[0] if result else None}


@router.patch("/{alert_id}/resolve")
def resolve_alert(alert_id: str, client: Client = Depends(admin_client)) -> dict:
    row = {"status": "resolved", "resolved_at": datetime.now(timezone.utc).isoformat()}
    result = client.table("alerts").update(row).eq("id", alert_id).execute().data
    return {"alert": result[0] if result else None}
