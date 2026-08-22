from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from supabase import Client


def risk_level(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def score_readings(latest: dict[str, Any] | None, history: list[dict[str, Any]], events: list[dict[str, Any]]) -> dict[str, Any]:
    score = 0
    reasons: list[str] = []
    component = "system"
    action = "Continue routine preventive maintenance."
    latest = latest or {}

    def add(points: int, reason: str, suspected: str, recommended: str) -> None:
        nonlocal score, component, action
        score += points
        reasons.append(reason)
        if component == "system" or points >= 20:
            component = suspected
            action = recommended

    recent_cpu = [r.get("cpu_usage") for r in history[:5] if r.get("cpu_usage") is not None]
    if len(recent_cpu) == 5 and all(value > 90 for value in recent_cpu):
        add(25, "CPU usage stayed above 90% for five consecutive readings.", "cpu", "Inspect runaway processes, cooling, and workload placement.")
    if latest.get("cpu_temperature") is not None and latest["cpu_temperature"] >= 85:
        add(20, "CPU temperature is abnormally high.", "cpu", "Clean cooling path, verify fans, and reduce sustained load.")

    if latest.get("fan_speed_rpm") is not None and latest["fan_speed_rpm"] >= 3000:
        add(8, "Fan speed is unusually high.", "cooling", "Inspect cooling demand, dust buildup, and fan bearing noise.")
    if latest.get("fan_speed_percent") is not None and latest["fan_speed_percent"] >= 90:
        add(8, "Fan speed is near maximum.", "cooling", "Inspect cooling demand, dust buildup, and fan bearing noise.")

    recent_ram = [r.get("ram_usage") for r in history[:5] if r.get("ram_usage") is not None]
    if len(recent_ram) >= 3 and sum(1 for value in recent_ram if value > 90) >= 3:
        add(18, "RAM usage is repeatedly above 90%.", "memory", "Review memory-heavy processes or plan a RAM upgrade.")

    if latest.get("disk_usage") is not None and latest["disk_usage"] > 90:
        add(18, "Disk usage is above 90%.", "disk", "Free storage, archive old data, or expand disk capacity.")
    if latest.get("disk_temperature") is not None and latest["disk_temperature"] >= 60:
        add(15, "Disk temperature is high.", "disk", "Improve airflow and verify drive bay cooling.")
    disk_health = (latest.get("disk_health") or "").lower()
    if disk_health in {"warning", "fail", "failed", "bad"}:
        add(35, "SMART health indicates a warning or failure state.", "disk", "Back up immediately and schedule disk replacement.")

    if latest.get("battery_health") is not None and latest["battery_health"] < 60:
        add(14, "Battery health is declining.", "battery", "Plan battery replacement and check charging behavior.")

    critical_events = [event for event in events if event.get("severity") == "critical"]
    if len(critical_events) >= 3:
        add(15, "Multiple critical Windows events were reported recently.", "operating_system", "Review Event Viewer errors and update drivers or failing applications.")
    if any("shutdown" in (event.get("message") or "").lower() for event in events):
        add(15, "Unexpected shutdown events were reported.", "power", "Check power stability, thermal events, and kernel power logs.")
    if any("antivirus" in (event.get("message") or "").lower() or "firewall" in (event.get("message") or "").lower() for event in events):
        add(20, "Security protection appears disabled or unhealthy.", "security", "Re-enable antivirus and firewall protections.")
    if any("update" in (event.get("message") or "").lower() for event in events):
        add(8, "Windows Update requires attention.", "operating_system", "Apply important Windows updates during a maintenance window.")

    if latest.get("network_latency") is not None and latest["network_latency"] > 200:
        add(10, "Network latency is high.", "network", "Check gateway reachability, cabling, Wi-Fi quality, and DNS.")
    if latest.get("packet_loss") is not None and latest["packet_loss"] > 5:
        add(15, "Packet loss is elevated.", "network", "Investigate network path quality and interface errors.")

    score = min(score, 100)
    if not reasons:
        reasons.append("No current high-risk diagnostic signals were found.")

    return {
        "risk_score": score,
        "risk_level": risk_level(score),
        "suspected_component": component,
        "reasons": reasons,
        "recommended_action": action,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def analyze_computer(client: Client, computer_id: str, save: bool = True) -> dict[str, Any]:
    readings = client.table("diagnostic_readings").select("*").eq("computer_id", computer_id).order("recorded_at", desc=True).limit(20).execute().data or []
    events = client.table("system_events").select("*").eq("computer_id", computer_id).order("occurred_at", desc=True).limit(50).execute().data or []
    result = score_readings(readings[0] if readings else None, readings, events)
    result["computer_id"] = computer_id
    if save:
        inserted = client.table("predictions").insert(result).execute().data
        if inserted:
            result = inserted[0]
    return result
