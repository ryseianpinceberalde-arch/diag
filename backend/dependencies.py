from fastapi import Depends, Header, HTTPException, status
from supabase import Client
from config import Settings, get_settings
from database import get_supabase_admin, get_supabase_anon


def require_agent_api_key(
    x_agent_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if not x_agent_api_key or x_agent_api_key != settings.agent_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid agent credentials")


def require_admin(
    authorization: str | None = Header(default=None),
    anon: Client = Depends(get_supabase_anon),
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
    return {"id": user.id, "email": user.email}


def admin_client() -> Client:
    return get_supabase_admin()
