from __future__ import annotations

import logging
from typing import Any

from supabase import Client

logger = logging.getLogger("pc_sentinel.notifications")


def upsert_alert_notification(
    client: Client,
    computer_id: str,
    alert_id: str | None,
    issue: dict[str, Any],
) -> None:
    if not alert_id:
        return
    try:
        existing = client.table("notifications").select("id").eq("alert_id", alert_id).limit(1).execute().data or []
        if existing:
            return
        notification_type = "critical_device" if issue.get("severity") == "critical" else "device_warning"
        client.table("notifications").insert(
            {
                "computer_id": computer_id,
                "alert_id": alert_id,
                "type": notification_type,
                "severity": issue.get("severity") or "high",
                "title": issue.get("title") or "Device issue detected",
                "message": issue.get("description") or "A monitoring rule detected a device issue.",
            }
        ).execute()
    except Exception:
        logger.warning("Notification sync failed for alert_id=%s", alert_id, exc_info=True)
