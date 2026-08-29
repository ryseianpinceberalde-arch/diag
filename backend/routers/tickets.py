from datetime import datetime, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from supabase import Client

from dependencies import admin_client, require_role

router = APIRouter(prefix="/tickets", tags=["tickets"])

TICKET_STATUSES = {"open", "assigned", "in_progress", "waiting_for_parts", "resolved", "verified", "closed", "cancelled"}
TICKET_SEVERITIES = {"info", "warning", "critical", "low", "medium", "high"}


class RepairTicketIn(BaseModel):
    computer_id: str
    diagnostic_finding_id: str | None = None
    assigned_technician_id: str | None = None
    severity: str = "medium"
    category: str = "manual"
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1, max_length=4000)


class RepairTicketUpdate(BaseModel):
    assigned_technician_id: str | None = None
    severity: str | None = None
    category: str | None = None
    title: str | None = None
    description: str | None = None
    status: str | None = None
    resolution: str | None = None
    verification_notes: str | None = None


def ticket_number() -> str:
    return f"RT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"


def attach_technicians(client: Client, rows: list[dict]) -> list[dict]:
    technician_ids = sorted({row["assigned_technician_id"] for row in rows if row.get("assigned_technician_id")})
    if not technician_ids:
        return rows
    profiles = client.table("profiles").select("id,full_name").in_("id", technician_ids).execute().data or []
    profiles_by_id = {profile["id"]: profile for profile in profiles}
    for row in rows:
        row["assigned_technician"] = profiles_by_id.get(row.get("assigned_technician_id"))
    return rows


@router.get("", dependencies=[Depends(require_role("administrator", "technician", "viewer"))])
def list_tickets(
    status: str | None = None,
    severity: str | None = None,
    computer_id: str | None = None,
    assigned_technician_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    client: Client = Depends(admin_client),
) -> dict:
    query = client.table("repair_tickets").select("*, computers(computer_name,device_id), diagnostic_findings(title,component,severity)", count="exact").order("created_at", desc=True)
    if status:
        query = query.eq("status", status)
    if severity:
        query = query.eq("severity", severity)
    if computer_id:
        query = query.eq("computer_id", computer_id)
    if assigned_technician_id:
        query = query.eq("assigned_technician_id", assigned_technician_id)
    result = query.range(offset, offset + limit - 1).execute()
    rows = attach_technicians(client, result.data or [])
    return {"items": rows, "total": result.count or 0, "limit": limit, "offset": offset}


@router.post("", dependencies=[Depends(require_role("administrator", "technician"))])
def create_ticket(
    payload: RepairTicketIn,
    user: dict = Depends(require_role("administrator", "technician")),
    client: Client = Depends(admin_client),
) -> dict:
    if payload.severity not in TICKET_SEVERITIES:
        raise HTTPException(status_code=422, detail="Invalid ticket severity")
    computer = client.table("computers").select("id").eq("id", payload.computer_id).limit(1).execute().data or []
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")
    row = payload.model_dump(mode="json")
    row["ticket_number"] = ticket_number()
    row["reported_by"] = user["id"]
    row["status"] = "assigned" if payload.assigned_technician_id else "open"
    result = client.table("repair_tickets").insert(row).execute().data
    ticket = result[0] if result else row
    client.table("audit_logs").insert(
        {
            "actor_id": user["id"],
            "action": "repair_ticket.create",
            "target_type": "repair_ticket",
            "target_id": ticket.get("id") or row["ticket_number"],
            "metadata": {"computer_id": payload.computer_id},
        }
    ).execute()
    return {"ticket": ticket}


@router.get("/{ticket_id}", dependencies=[Depends(require_role("administrator", "technician", "viewer"))])
def get_ticket(ticket_id: str, client: Client = Depends(admin_client)) -> dict:
    rows = client.table("repair_tickets").select("*, computers(computer_name,device_id), diagnostic_findings(title,component,severity)").eq("id", ticket_id).limit(1).execute().data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Repair ticket not found")
    return {"ticket": attach_technicians(client, rows)[0]}


@router.patch("/{ticket_id}", dependencies=[Depends(require_role("administrator", "technician"))])
def update_ticket(
    ticket_id: str,
    payload: RepairTicketUpdate,
    user: dict = Depends(require_role("administrator", "technician")),
    client: Client = Depends(admin_client),
) -> dict:
    row = payload.model_dump(exclude_none=True, mode="json")
    if "status" in row and row["status"] not in TICKET_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid ticket status")
    if "severity" in row and row["severity"] not in TICKET_SEVERITIES:
        raise HTTPException(status_code=422, detail="Invalid ticket severity")
    row["updated_at"] = datetime.now(timezone.utc).isoformat()
    if row.get("status") == "resolved":
        row["resolved_at"] = row["updated_at"]
    if row.get("status") == "verified":
        row["verified_at"] = row["updated_at"]
    if row.get("status") == "closed":
        row["closed_at"] = row["updated_at"]
    result = client.table("repair_tickets").update(row).eq("id", ticket_id).execute().data
    client.table("audit_logs").insert(
        {
            "actor_id": user["id"],
            "action": "repair_ticket.update",
            "target_type": "repair_ticket",
            "target_id": ticket_id,
            "metadata": row,
        }
    ).execute()
    return {"ticket": result[0] if result else None}
