from fastapi import APIRouter, Depends
from supabase import Client
from dependencies import admin_client, require_admin

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(require_admin)])


@router.get("/maintenance")
def maintenance_report(client: Client = Depends(admin_client)) -> dict:
    predictions = client.table("predictions").select("*, computers(computer_name, device_id)").order("created_at", desc=True).limit(100).execute().data or []
    return {
        "items": [
            {
                "computer": row.get("computers"),
                "risk_level": row.get("risk_level"),
                "risk_score": row.get("risk_score"),
                "component": row.get("suspected_component"),
                "recommendation": row.get("recommended_action"),
                "created_at": row.get("created_at"),
            }
            for row in predictions
        ]
    }
