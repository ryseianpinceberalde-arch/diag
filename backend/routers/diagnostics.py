from datetime import datetime, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from supabase import Client

from dependencies import admin_client, require_role

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])

FINDING_STATUSES = {"active", "acknowledged", "resolved", "ignored"}


class FindingUpdate(BaseModel):
    status: str | None = None


class TicketFromFindingIn(BaseModel):
    assigned_technician_id: str | None = None


def ticket_number() -> str:
    return f"RT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"


@router.get("", dependencies=[Depends(require_role("administrator", "technician", "viewer"))])
def list_findings(
    status: str | None = None,
    severity: str | None = None,
    component: str | None = None,
    computer_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    client: Client = Depends(admin_client),
) -> dict:
    query = client.table("diagnostic_findings").select("*, computers(computer_name,device_id,department_id,location_id)", count="exact").order("last_detected_at", desc=True)
    if status:
        query = query.eq("status", status)
    if severity:
        query = query.eq("severity", severity)
    if component:
        query = query.eq("component", component)
    if computer_id:
        query = query.eq("computer_id", computer_id)
    result = query.range(offset, offset + limit - 1).execute()
    return {"items": result.data or [], "total": result.count or 0, "limit": limit, "offset": offset}


@router.get("/{finding_id}", dependencies=[Depends(require_role("administrator", "technician", "viewer"))])
def get_finding(finding_id: str, client: Client = Depends(admin_client)) -> dict:
    rows = client.table("diagnostic_findings").select("*, computers(computer_name,device_id)").eq("id", finding_id).limit(1).execute().data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Diagnostic finding not found")
    return {"finding": rows[0]}


@router.patch("/{finding_id}", dependencies=[Depends(require_role("administrator", "technician"))])
def update_finding(
    finding_id: str,
    payload: FindingUpdate,
    user: dict = Depends(require_role("administrator", "technician")),
    client: Client = Depends(admin_client),
) -> dict:
    row = payload.model_dump(exclude_none=True)
    if "status" in row and row["status"] not in FINDING_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid finding status")
    row["updated_at"] = datetime.now(timezone.utc).isoformat()
    if row.get("status") == "resolved":
        row["resolved_at"] = row["updated_at"]
    result = client.table("diagnostic_findings").update(row).eq("id", finding_id).execute().data
    client.table("audit_logs").insert(
        {
            "actor_id": user["id"],
            "action": "diagnostic_finding.update",
            "target_type": "diagnostic_finding",
            "target_id": finding_id,
            "metadata": row,
        }
    ).execute()
    return {"finding": result[0] if result else None}


@router.post("/{finding_id}/ticket", dependencies=[Depends(require_role("administrator", "technician"))])
def create_ticket_from_finding(
    finding_id: str,
    payload: TicketFromFindingIn,
    user: dict = Depends(require_role("administrator", "technician")),
    client: Client = Depends(admin_client),
) -> dict:
    findings = client.table("diagnostic_findings").select("*").eq("id", finding_id).limit(1).execute().data or []
    if not findings:
        raise HTTPException(status_code=404, detail="Diagnostic finding not found")
    finding = findings[0]
    existing = (
        client.table("repair_tickets")
        .select("*")
        .eq("diagnostic_finding_id", finding_id)
        .in_("status", ["open", "assigned", "in_progress", "waiting_for_parts"])
        .limit(1)
        .execute()
        .data
        or []
    )
    if existing:
        return {"ticket": existing[0], "created": False}
    status = "assigned" if payload.assigned_technician_id else "open"
    row = {
        "ticket_number": ticket_number(),
        "computer_id": finding["computer_id"],
        "diagnostic_finding_id": finding_id,
        "reported_by": user["id"],
        "assigned_technician_id": payload.assigned_technician_id,
        "severity": finding["severity"],
        "category": finding.get("component") or "diagnostics",
        "title": finding.get("title") or "Diagnostic finding",
        "description": finding.get("recommendation") or finding.get("description") or "",
        "status": status,
    }
    result = client.table("repair_tickets").insert(row).execute().data
    ticket = result[0] if result else row
    client.table("audit_logs").insert(
        {
            "actor_id": user["id"],
            "action": "repair_ticket.created_from_finding",
            "target_type": "repair_ticket",
            "target_id": ticket.get("id") or row["ticket_number"],
            "metadata": {"diagnostic_finding_id": finding_id},
        }
    ).execute()
    return {"ticket": ticket, "created": True}
