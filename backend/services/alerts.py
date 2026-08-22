from __future__ import annotations

from typing import Any
from supabase import Client
from services.prediction import analyze_computer


def upsert_prediction_alerts(client: Client, computer_id: str) -> dict[str, Any]:
    prediction = analyze_computer(client, computer_id, save=True)
    score = prediction["risk_score"]
    if score < 35:
        return prediction

    title = f"{prediction['risk_level'].title()} risk detected for {prediction['suspected_component']}"
    payload = {
        "computer_id": computer_id,
        "category": "prediction",
        "severity": "critical" if score >= 85 else "high" if score >= 65 else "medium",
        "title": title,
        "description": prediction["recommended_action"],
        "status": "active",
    }
    existing = client.table("alerts").select("id").eq("computer_id", computer_id).eq("category", "prediction").eq("title", title).in_("status", ["active", "acknowledged"]).limit(1).execute().data
    if not existing:
        client.table("alerts").insert(payload).execute()
    return prediction
