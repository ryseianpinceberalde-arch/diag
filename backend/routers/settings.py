from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from dependencies import admin_client, require_role
from services.settings import default_threshold_dict, load_thresholds, validate_threshold_update

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", dependencies=[Depends(require_role("administrator", "technician", "viewer"))])
def get_settings(client: Client = Depends(admin_client)) -> dict:
    thresholds = load_thresholds(client)
    return {"settings": thresholds.__dict__}


@router.patch("", dependencies=[Depends(require_role("administrator"))])
def update_settings(payload: dict, user: dict = Depends(require_role("administrator")), client: Client = Depends(admin_client)) -> dict:
    try:
        clean = validate_threshold_update(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    existing = default_threshold_dict()
    for key, value in clean.items():
        if key not in existing:
            continue
        stored_value = list(value) if isinstance(value, tuple) else value
        client.table("app_settings").upsert(
            {"key": key, "value": stored_value, "updated_by": user["id"]},
            on_conflict="key",
        ).execute()
    client.table("audit_logs").insert({"actor_id": user["id"], "action": "settings.update", "metadata": clean}).execute()
    return {"settings": load_thresholds(client).__dict__}
