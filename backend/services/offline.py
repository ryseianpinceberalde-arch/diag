import logging
from datetime import datetime, timezone

from supabase import Client

from services.settings import load_thresholds
from services.status import parse_timestamp

logger = logging.getLogger("pc_sentinel.offline")


def mark_stale_computers(client: Client) -> int:
    """Persist offline state without creating a duplicate alert per sweep."""
    thresholds = load_thresholds(client)
    rows = client.table("computers").select("id,last_seen,status").execute().data or []
    now = datetime.now(timezone.utc)
    stale_ids = []
    for row in rows:
        last_seen = parse_timestamp(row.get("last_seen"))
        if not last_seen or (now - last_seen).total_seconds() > thresholds.offline_after_seconds:
            if row.get("status") != "offline":
                stale_ids.append(row["id"])
    for computer_id in stale_ids:
        client.table("computers").update({"status": "offline"}).eq("id", computer_id).execute()
    return len(stale_ids)
