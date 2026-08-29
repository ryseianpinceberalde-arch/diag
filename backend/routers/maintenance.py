from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
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


class MaintenanceRecordIn(BaseModel):
    computer_id: str
    ticket_id: str | None = None
    maintenance_type: str = "preventive"
    problem_description: str | None = None
    actions_taken: str | None = None
    parts_replaced: str | None = None
    technician_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: str = "scheduled"
    notes: str | None = None


class MaintenanceRecordUpdate(BaseModel):
    maintenance_type: str | None = None
    problem_description: str | None = None
    actions_taken: str | None = None
    parts_replaced: str | None = None
    technician_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: str | None = None
    notes: str | None = None


MAINTENANCE_TYPES = {"preventive", "corrective", "inspection", "cleaning", "software", "hardware"}
MAINTENANCE_STATUSES = {"scheduled", "in_progress", "completed", "cancelled"}


def attach_maintenance_technicians(client: Client, rows: list[dict]) -> list[dict]:
    technician_ids = sorted({row["technician_id"] for row in rows if row.get("technician_id")})
    if not technician_ids:
        return rows
    profiles = client.table("profiles").select("id,full_name").in_("id", technician_ids).execute().data or []
    profiles_by_id = {profile["id"]: profile for profile in profiles}
    for row in rows:
        row["technician"] = profiles_by_id.get(row.get("technician_id"))
    return rows


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


@router.get("/records", dependencies=[Depends(require_role("administrator", "technician", "viewer"))])
def list_maintenance_records(
    status: str | None = None,
    computer_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    client: Client = Depends(admin_client),
) -> dict:
    query = client.table("maintenance_records").select("*, computers(computer_name,device_id), repair_tickets(ticket_number,title)", count="exact").order("created_at", desc=True)
    if status:
        query = query.eq("status", status)
    if computer_id:
        query = query.eq("computer_id", computer_id)
    result = query.range(offset, offset + limit - 1).execute()
    rows = attach_maintenance_technicians(client, result.data or [])
    return {"items": rows, "total": result.count or 0, "limit": limit, "offset": offset}


@router.post("/records", dependencies=[Depends(require_role("administrator", "technician"))])
def create_maintenance_record(
    payload: MaintenanceRecordIn,
    user: dict = Depends(require_role("administrator", "technician")),
    client: Client = Depends(admin_client),
) -> dict:
    if payload.maintenance_type not in MAINTENANCE_TYPES:
        raise HTTPException(status_code=422, detail="Invalid maintenance type")
    if payload.status not in MAINTENANCE_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid maintenance status")
    row = payload.model_dump(mode="json", exclude_none=True)
    result = client.table("maintenance_records").insert(row).execute().data
    record = result[0] if result else row
    client.table("audit_logs").insert({"actor_id": user["id"], "action": "maintenance_record.create", "target_type": "maintenance_record", "target_id": record.get("id"), "metadata": {"computer_id": payload.computer_id}}).execute()
    return {"record": record}


@router.patch("/records/{record_id}", dependencies=[Depends(require_role("administrator", "technician"))])
def update_maintenance_record(
    record_id: str,
    payload: MaintenanceRecordUpdate,
    user: dict = Depends(require_role("administrator", "technician")),
    client: Client = Depends(admin_client),
) -> dict:
    row = payload.model_dump(exclude_none=True, mode="json")
    if "maintenance_type" in row and row["maintenance_type"] not in MAINTENANCE_TYPES:
        raise HTTPException(status_code=422, detail="Invalid maintenance type")
    if "status" in row and row["status"] not in MAINTENANCE_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid maintenance status")
    row["updated_at"] = datetime.now(timezone.utc).isoformat()
    if row.get("status") == "completed" and "completed_at" not in row:
        row["completed_at"] = row["updated_at"]
    result = client.table("maintenance_records").update(row).eq("id", record_id).execute().data
    client.table("audit_logs").insert({"actor_id": user["id"], "action": "maintenance_record.update", "target_type": "maintenance_record", "target_id": record_id, "metadata": row}).execute()
    return {"record": result[0] if result else None}


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
