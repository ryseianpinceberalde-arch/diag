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
    stale_rows = []
    for row in rows:
        last_seen = parse_timestamp(row.get("last_seen"))
        if not last_seen or (now - last_seen).total_seconds() > thresholds.offline_after_seconds:
            if row.get("status") != "offline":
                stale_rows.append(row)
    updated = 0
    for row in stale_rows:
        query = client.table("computers").update({"status": "offline"}).eq("id", row["id"])
        # Do not overwrite a heartbeat received after this sweep's snapshot.
        if row.get("last_seen") is None:
            query = query.is_("last_seen", "null")
        else:
            query = query.eq("last_seen", row["last_seen"])
        updated += len(query.execute().data or [])
    return updated
