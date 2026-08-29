from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from supabase import Client
from services.health import evaluate_computer_health
from services.prediction import analyze_computer
from services.settings import load_thresholds
from services.diagnostics import sync_diagnostic_findings
from services.notifications import upsert_alert_notification


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_health_alerts(client: Client, computer: dict[str, Any], latest_reading: dict[str, Any] | None) -> dict[str, Any]:
    thresholds = load_thresholds(client)
    health = evaluate_computer_health(computer, latest_reading, thresholds)
    issue_keys = {issue["alert_key"] for issue in health["issues"]}
    alert_ids: dict[str, str | None] = {}

    for issue in health["issues"]:
        existing = (
            client.table("alerts")
            .select("id,occurrence_count,status")
            .eq("computer_id", computer["id"])
            .eq("alert_key", issue["alert_key"])
            .in_("status", ["active", "acknowledged"])
            .limit(1)
            .execute()
            .data
            or []
        )
        payload = {
            "computer_id": computer["id"],
            "category": issue["problem_type"],
            "component": issue["component"],
            "alert_key": issue["alert_key"],
            "severity": issue["severity"],
            "title": issue["title"],
            "description": issue["description"],
            "measured_value": issue["measured_value"],
            "threshold_value": issue["threshold_value"],
            "last_detected_at": now_iso(),
            "recovery_count": 0,
            "status": "active",
        }
        alert_id = None
        if existing:
            payload["occurrence_count"] = int(existing[0].get("occurrence_count") or 1) + 1
            updated = client.table("alerts").update(payload).eq("id", existing[0]["id"]).execute().data or []
            alert_id = updated[0].get("id") if updated else existing[0]["id"]
        else:
            payload["first_detected_at"] = payload["last_detected_at"]
            payload["occurrence_count"] = 1
            inserted = client.table("alerts").insert(payload).execute().data or []
            alert_id = inserted[0].get("id") if inserted else None
        alert_ids[issue["alert_key"]] = alert_id
        if issue["severity"] == "critical":
            upsert_alert_notification(client, computer["id"], alert_id, issue)
        if issue["severity"] in {"high", "critical"}:
            upsert_maintenance_ticket(client, computer["id"], issue, alert_id)

    sync_diagnostic_findings(client, computer, health["issues"], alert_ids)

    active = (
        client.table("alerts")
        .select("id,alert_key,recovery_count")
        .eq("computer_id", computer["id"])
        .in_("status", ["active", "acknowledged"])
        .execute()
        .data
        or []
    )
    for alert in active:
        key = alert.get("alert_key")
        if not key or key in issue_keys:
            continue
        recovery_count = int(alert.get("recovery_count") or 0) + 1
        if recovery_count >= thresholds.alert_recovery_readings:
            client.table("alerts").update({"status": "resolved", "resolved_at": now_iso(), "recovery_count": recovery_count}).eq("id", alert["id"]).execute()
        else:
            client.table("alerts").update({"recovery_count": recovery_count}).eq("id", alert["id"]).execute()

    client.table("computers").update({"status": health["status"]}).eq("id", computer["id"]).execute()
    return health


def upsert_maintenance_ticket(client: Client, computer_id: str, issue: dict[str, Any], alert_id: str | None = None) -> None:
    ticket_key = f"{computer_id}:{issue['component']}:{issue['problem_type']}"
    priority = "critical" if issue["severity"] == "critical" else "high"
    row = {
        "ticket_key": ticket_key,
        "computer_id": computer_id,
        "alert_id": alert_id,
        "component": issue["component"],
        "problem_type": issue["problem_type"],
        "title": issue["title"],
        "description": issue["description"],
        "priority": priority,
        "status": "pending",
    }
    try:
        existing = client.table("maintenance_tickets").select("id,status").eq("ticket_key", ticket_key).in_("status", ["pending", "in_progress"]).limit(1).execute().data or []
        if existing:
            client.table("maintenance_tickets").update({k: v for k, v in row.items() if k not in {"ticket_key", "computer_id", "status"}}).eq("id", existing[0]["id"]).execute()
        else:
            client.table("maintenance_tickets").insert(row).execute()
    except Exception:
        pass


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
        payload.update({
            "component": prediction["suspected_component"],
            "alert_key": f"prediction:{prediction['suspected_component']}:{prediction['risk_level']}",
            "first_detected_at": now_iso(),
            "last_detected_at": now_iso(),
            "occurrence_count": 1,
        })
        client.table("alerts").insert(payload).execute()
    return prediction
