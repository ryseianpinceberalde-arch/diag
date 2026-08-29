import logging
from fastapi import APIRouter, Depends
from supabase import Client
from dependencies import admin_client, require_admin
from services.health import evaluate_computer_health
from services.settings import load_thresholds
from services.status import effective_status

router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(require_admin)])
logger = logging.getLogger("pc_sentinel.dashboard")


@router.get("/summary")
def dashboard_summary(client: Client = Depends(admin_client)) -> dict:
    thresholds = load_thresholds(client)
    computers = client.table("computers").select("*").execute().data or []
    latest_readings = client.table("diagnostic_readings").select("*").order("recorded_at", desc=True).limit(500).execute().data or []
    alerts = client.table("alerts").select("id", count="exact").in_("status", ["active", "acknowledged"]).execute()
    try:
        tickets = client.table("repair_tickets").select("id,status", count="exact").in_("status", ["open", "assigned", "in_progress", "waiting_for_parts"]).execute()
        open_tickets = tickets.count or 0
    except Exception:
        try:
            tickets = client.table("maintenance_tickets").select("id,status", count="exact").in_("status", ["pending", "in_progress"]).execute()
            open_tickets = tickets.count or 0
        except Exception:
            # Older deployments may not have the additive maintenance migration yet.
            logger.warning("Could not load ticket count; continuing dashboard summary", exc_info=True)
            open_tickets = 0
    predictions = client.table("predictions").select("computer_id,risk_score,risk_level").order("created_at", desc=True).limit(200).execute().data or []
    latest_predictions = {}
    for prediction in predictions:
        latest_predictions.setdefault(prediction.get("computer_id"), prediction)
    scores = [row["risk_score"] for row in predictions if row.get("risk_score") is not None]
    latest_by_computer = {}
    for reading in latest_readings:
        latest_by_computer.setdefault(reading.get("computer_id"), reading)
    trends = [
        {"time": row.get("recorded_at"), "cpu": row.get("cpu_usage"), "ram": row.get("ram_usage"), "disk": row.get("disk_usage")}
        for row in reversed(latest_readings[:24])
    ]
    cpu_temps = [row["cpu_temperature"] for row in latest_by_computer.values() if row.get("cpu_temperature") is not None]
    disk_temps = [row["disk_temperature"] for row in latest_by_computer.values() if row.get("disk_temperature") is not None]
    fan_speeds = [row["fan_speed_rpm"] for row in latest_by_computer.values() if row.get("fan_speed_rpm") is not None]
    fan_percentages = [row["fan_speed_percent"] for row in latest_by_computer.values() if row.get("fan_speed_percent") is not None]
    health_results = [
        evaluate_computer_health(computer, latest_by_computer.get(computer.get("id")), thresholds)
        for computer in computers
    ]
    health_levels = [result["status"] for result in health_results]
    connection_statuses = [effective_status(computer, offline_after_seconds=thresholds.offline_after_seconds) for computer in computers]
    system_status = "critical" if any(level in {"critical", "offline"} for level in health_levels) else "warning" if any(level == "warning" for level in health_levels) else "healthy"
    return {
        "total_computers": len(computers),
        "online_computers": sum(1 for status in connection_statuses if status == "online"),
        "offline_computers": sum(1 for status in connection_statuses if status == "offline"),
        "healthy_computers": sum(1 for level in health_levels if level == "healthy"),
        "warning_computers": sum(1 for level in health_levels if level == "warning"),
        "critical_computers": sum(1 for level in health_levels if level == "critical"),
        "system_status": system_status,
        "active_alerts": alerts.count or 0,
        "open_tickets": open_tickets,
        "trends": trends,
        "average_risk_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "average_cpu_temperature": round(sum(cpu_temps) / len(cpu_temps), 1) if cpu_temps else None,
        "max_cpu_temperature": round(max(cpu_temps), 1) if cpu_temps else None,
        "average_disk_temperature": round(sum(disk_temps) / len(disk_temps), 1) if disk_temps else None,
        "max_disk_temperature": round(max(disk_temps), 1) if disk_temps else None,
        "average_fan_speed_rpm": round(sum(fan_speeds) / len(fan_speeds), 0) if fan_speeds else None,
        "average_fan_speed_percent": round(sum(fan_percentages) / len(fan_percentages), 1) if fan_percentages else None,
    }
