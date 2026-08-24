from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from supabase import Client

from dependencies import admin_client, require_role

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


class TicketIn(BaseModel):
    computer_id: str
    component: str
    problem_type: str
    title: str
    description: str
    priority: str = "medium"
    assigned_technician: str | None = None
    due_date: date | None = None


class TicketUpdate(BaseModel):
    status: str | None = None
    priority: str | None = None
    assigned_technician: str | None = None
    due_date: date | None = None
    technician_notes: str | None = None
    resolution_description: str | None = None


@router.get("", dependencies=[Depends(require_role("administrator", "technician", "viewer"))])
def list_tickets(
    status: str | None = None,
    computer_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    client: Client = Depends(admin_client),
) -> dict:
    query = client.table("maintenance_tickets").select("*, computers(computer_name,device_id)", count="exact").order("created_at", desc=True)
    if status:
        query = query.eq("status", status)
    if computer_id:
        query = query.eq("computer_id", computer_id)
    result = query.range(offset, offset + limit - 1).execute()
    return {"items": result.data or [], "total": result.count or 0}


@router.post("", dependencies=[Depends(require_role("administrator"))])
def create_ticket(payload: TicketIn, user: dict = Depends(require_role("administrator")), client: Client = Depends(admin_client)) -> dict:
    ticket_key = f"{payload.computer_id}:{payload.component}:{payload.problem_type}"
    row = payload.model_dump(mode="json")
    row["ticket_key"] = ticket_key
    existing = client.table("maintenance_tickets").select("id").eq("ticket_key", ticket_key).in_("status", ["pending", "in_progress"]).limit(1).execute().data or []
    if existing:
        result = client.table("maintenance_tickets").update(row).eq("id", existing[0]["id"]).execute().data
    else:
        result = client.table("maintenance_tickets").insert(row).execute().data
    client.table("audit_logs").insert({"actor_id": user["id"], "action": "maintenance.create", "target_id": result[0]["id"] if result else ticket_key}).execute()
    return {"ticket": result[0] if result else row}


@router.patch("/{ticket_id}", dependencies=[Depends(require_role("administrator", "technician"))])
def update_ticket(ticket_id: str, payload: TicketUpdate, user: dict = Depends(require_role("administrator", "technician")), client: Client = Depends(admin_client)) -> dict:
    row = payload.model_dump(exclude_none=True, mode="json")
    row["updated_at"] = datetime.now(timezone.utc).isoformat()
    if row.get("status") == "completed":
        row["completed_at"] = row["updated_at"]
    result = client.table("maintenance_tickets").update(row).eq("id", ticket_id).execute().data
    client.table("audit_logs").insert({"actor_id": user["id"], "action": "maintenance.update", "target_id": ticket_id, "metadata": row}).execute()
    return {"ticket": result[0] if result else None}
