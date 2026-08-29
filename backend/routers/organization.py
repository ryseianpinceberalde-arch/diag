from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from supabase import Client

from dependencies import admin_client, require_role

router = APIRouter(tags=["organization"])


class DepartmentIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None


class LocationIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    building: str | None = None
    room: str | None = None
    description: str | None = None


@router.get("/departments", dependencies=[Depends(require_role("administrator", "technician", "viewer"))])
def list_departments(client: Client = Depends(admin_client)) -> dict:
    rows = client.table("departments").select("*").order("name").execute().data or []
    return {"items": rows}


@router.post("/departments", dependencies=[Depends(require_role("administrator"))])
def create_department(payload: DepartmentIn, user: dict = Depends(require_role("administrator")), client: Client = Depends(admin_client)) -> dict:
    result = client.table("departments").insert(payload.model_dump(mode="json")).execute().data
    department = result[0] if result else payload.model_dump(mode="json")
    client.table("audit_logs").insert({"actor_id": user["id"], "action": "department.create", "target_type": "department", "target_id": department.get("id"), "metadata": {"name": payload.name}}).execute()
    return {"department": department}


@router.patch("/departments/{department_id}", dependencies=[Depends(require_role("administrator"))])
def update_department(department_id: str, payload: DepartmentIn, user: dict = Depends(require_role("administrator")), client: Client = Depends(admin_client)) -> dict:
    result = client.table("departments").update(payload.model_dump(mode="json")).eq("id", department_id).execute().data
    if not result:
        raise HTTPException(status_code=404, detail="Department not found")
    client.table("audit_logs").insert({"actor_id": user["id"], "action": "department.update", "target_type": "department", "target_id": department_id}).execute()
    return {"department": result[0]}


@router.get("/locations", dependencies=[Depends(require_role("administrator", "technician", "viewer"))])
def list_locations(client: Client = Depends(admin_client)) -> dict:
    rows = client.table("locations").select("*").order("name").execute().data or []
    return {"items": rows}


@router.post("/locations", dependencies=[Depends(require_role("administrator"))])
def create_location(payload: LocationIn, user: dict = Depends(require_role("administrator")), client: Client = Depends(admin_client)) -> dict:
    result = client.table("locations").insert(payload.model_dump(mode="json")).execute().data
    location = result[0] if result else payload.model_dump(mode="json")
    client.table("audit_logs").insert({"actor_id": user["id"], "action": "location.create", "target_type": "location", "target_id": location.get("id"), "metadata": {"name": payload.name}}).execute()
    return {"location": location}


@router.patch("/locations/{location_id}", dependencies=[Depends(require_role("administrator"))])
def update_location(location_id: str, payload: LocationIn, user: dict = Depends(require_role("administrator")), client: Client = Depends(admin_client)) -> dict:
    result = client.table("locations").update(payload.model_dump(mode="json")).eq("id", location_id).execute().data
    if not result:
        raise HTTPException(status_code=404, detail="Location not found")
    client.table("audit_logs").insert({"actor_id": user["id"], "action": "location.update", "target_type": "location", "target_id": location_id}).execute()
    return {"location": result[0]}
