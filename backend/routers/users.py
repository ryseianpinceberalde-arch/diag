from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from supabase import Client

from dependencies import admin_client, require_role

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_role("administrator"))])


class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=6)
    full_name: str | None = None
    role: str = "viewer"

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("Invalid email")
        return value.lower()


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None


@router.get("")
def list_users(client: Client = Depends(admin_client)) -> dict:
    rows = client.table("profiles").select("*").order("created_at", desc=True).execute().data or []
    return {"items": rows}


@router.post("")
def create_user(payload: UserCreate, actor: dict = Depends(require_role("administrator")), client: Client = Depends(admin_client)) -> dict:
    if payload.role not in {"administrator", "technician", "viewer"}:
        raise HTTPException(status_code=422, detail="Invalid role")
    created = client.auth.admin.create_user(
        {
            "email": payload.email,
            "password": payload.password,
            "email_confirm": True,
        }
    )
    user = created.user
    if not user:
        raise HTTPException(status_code=400, detail="Unable to create user")
    profile = {
        "id": user.id,
        "email": payload.email,
        "full_name": payload.full_name,
        "role": payload.role,
        "is_active": True,
    }
    client.table("profiles").upsert(profile).execute()
    client.table("audit_logs").insert({"actor_id": actor["id"], "action": "users.create", "target_id": user.id, "metadata": {"email": payload.email, "role": payload.role}}).execute()
    return {"user": profile}


@router.patch("/{user_id}")
def update_user(user_id: str, payload: UserUpdate, actor: dict = Depends(require_role("administrator")), client: Client = Depends(admin_client)) -> dict:
    row = payload.model_dump(exclude_none=True)
    if "role" in row and row["role"] not in {"administrator", "technician", "viewer"}:
        raise HTTPException(status_code=422, detail="Invalid role")
    updated = client.table("profiles").update(row).eq("id", user_id).execute().data
    client.table("audit_logs").insert({"actor_id": actor["id"], "action": "users.update", "target_id": user_id, "metadata": row}).execute()
    return {"user": updated[0] if updated else None}


@router.post("/{user_id}/password-reset")
def reset_password(user_id: str, actor: dict = Depends(require_role("administrator")), client: Client = Depends(admin_client)) -> dict:
    profile = client.table("profiles").select("email").eq("id", user_id).limit(1).execute().data or []
    if not profile or not profile[0].get("email"):
        raise HTTPException(status_code=404, detail="User email not found")
    client.auth.reset_password_email(profile[0]["email"])
    client.table("audit_logs").insert({"actor_id": actor["id"], "action": "users.password_reset", "target_id": user_id}).execute()
    return {"ok": True}
