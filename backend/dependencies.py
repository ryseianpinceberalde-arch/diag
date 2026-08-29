import hashlib
from fastapi import Depends, Header, HTTPException, status
from supabase import Client
from config import Settings, get_settings
from database import get_supabase_admin, get_supabase_anon

ROLE_ALIASES = {
    "super_admin": "administrator",
    "it_admin": "administrator",
    "department_user": "viewer",
}


def normalize_role(role: str | None) -> str:
    normalized = (role or "administrator").lower()
    return ROLE_ALIASES.get(normalized, normalized)


def require_agent_api_key(
    x_agent_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if not x_agent_api_key or x_agent_api_key != settings.agent_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid agent credentials")


def require_agent_credential(
    x_agent_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    admin: Client = Depends(get_supabase_admin),
) -> None:
    if x_agent_api_key and x_agent_api_key == settings.agent_api_key:
        return
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid agent credentials")
    token = authorization.split(" ", 1)[1].strip()
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    rows = admin.table("computers").select("id").eq("agent_token_hash", token_hash).limit(1).execute().data or []
    if not rows:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid agent credentials")


def require_admin(
    authorization: str | None = Header(default=None),
    anon: Client = Depends(get_supabase_anon),
    admin: Client = Depends(get_supabase_admin),
) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        user_response = anon.auth.get_user(token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token") from exc
    user = user_response.user
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token")
    profile = admin.table("profiles").select("role").eq("id", user.id).limit(1).execute().data or []
    role = normalize_role(profile[0].get("role") if profile else "administrator")
    if role not in {"administrator", "technician", "viewer"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive or unauthorized user")
    return {"id": user.id, "email": user.email, "role": role}


def require_role(*allowed_roles: str):
    def dependency(
        authorization: str | None = Header(default=None),
        anon: Client = Depends(get_supabase_anon),
        admin: Client = Depends(get_supabase_admin),
    ) -> dict:
        user = require_admin(authorization, anon, admin)
        profile = admin.table("profiles").select("role").eq("id", user["id"]).limit(1).execute().data or []
        role = normalize_role(profile[0].get("role") if profile else "administrator")
        if role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        user["role"] = role
        return user

    return dependency


def admin_client() -> Client:
    return get_supabase_admin()
