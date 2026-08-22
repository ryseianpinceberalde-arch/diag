from fastapi import APIRouter, Depends
from supabase import Client
from dependencies import admin_client, require_admin
from services.status import effective_status, health_from_prediction

router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(require_admin)])


@router.get("/summary")
def dashboard_summary(client: Client = Depends(admin_client)) -> dict:
    computers = client.table("computers").select("id,status,last_seen").execute().data or []
    latest_readings = client.table("diagnostic_readings").select(
        "computer_id,cpu_temperature,disk_temperature,fan_speed_rpm,fan_speed_percent,recorded_at"
    ).order("recorded_at", desc=True).limit(500).execute().data or []
    alerts = client.table("alerts").select("id", count="exact").in_("status", ["active", "acknowledged"]).execute()
    predictions = client.table("predictions").select("computer_id,risk_score,risk_level").order("created_at", desc=True).limit(200).execute().data or []
    latest_predictions = {}
    for prediction in predictions:
        latest_predictions.setdefault(prediction.get("computer_id"), prediction)
    scores = [row["risk_score"] for row in predictions if row.get("risk_score") is not None]
    latest_by_computer = {}
    for reading in latest_readings:
        latest_by_computer.setdefault(reading.get("computer_id"), reading)
    cpu_temps = [row["cpu_temperature"] for row in latest_by_computer.values() if row.get("cpu_temperature") is not None]
    disk_temps = [row["disk_temperature"] for row in latest_by_computer.values() if row.get("disk_temperature") is not None]
    fan_speeds = [row["fan_speed_rpm"] for row in latest_by_computer.values() if row.get("fan_speed_rpm") is not None]
    fan_percentages = [row["fan_speed_percent"] for row in latest_by_computer.values() if row.get("fan_speed_percent") is not None]
    statuses = [effective_status(computer) for computer in computers]
    health_levels = [
        health_from_prediction(latest_predictions.get(computer.get("id")), status)
        for computer, status in zip(computers, statuses)
    ]
    return {
        "total_computers": len(computers),
        "online_computers": sum(1 for status in statuses if status == "online"),
        "offline_computers": sum(1 for status in statuses if status == "offline"),
        "healthy_computers": sum(1 for level in health_levels if level == "healthy"),
        "warning_computers": sum(1 for level in health_levels if level == "warning"),
        "critical_computers": sum(1 for level in health_levels if level == "critical"),
        "active_alerts": alerts.count or 0,
        "average_risk_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "average_cpu_temperature": round(sum(cpu_temps) / len(cpu_temps), 1) if cpu_temps else None,
        "max_cpu_temperature": round(max(cpu_temps), 1) if cpu_temps else None,
        "average_disk_temperature": round(sum(disk_temps) / len(disk_temps), 1) if disk_temps else None,
        "max_disk_temperature": round(max(disk_temps), 1) if disk_temps else None,
        "average_fan_speed_rpm": round(sum(fan_speeds) / len(fan_speeds), 0) if fan_speeds else None,
        "average_fan_speed_percent": round(sum(fan_percentages) / len(fan_percentages), 1) if fan_percentages else None,
    }
