from fastapi import APIRouter, Depends, Query
from supabase import Client

from dependencies import admin_client, require_role

router = APIRouter(prefix="/audit-logs", tags=["audit"], dependencies=[Depends(require_role("administrator"))])


@router.get("")
def list_audit_logs(
    action: str | None = None,
    target_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    client: Client = Depends(admin_client),
) -> dict:
    query = client.table("audit_logs").select("*", count="exact").order("created_at", desc=True)
    if action:
        query = query.eq("action", action)
    if target_type:
        query = query.eq("target_type", target_type)
    result = query.range(offset, offset + limit - 1).execute()
    return {"items": result.data or [], "total": result.count or 0, "limit": limit, "offset": offset}
