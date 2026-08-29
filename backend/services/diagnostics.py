from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from supabase import Client

from services.settings import load_thresholds

logger = logging.getLogger("pc_sentinel.diagnostics")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def finding_severity(issue: dict[str, Any]) -> str:
    return "critical" if issue.get("severity") == "critical" else "warning"


def issue_context(issue: dict[str, Any]) -> tuple[str, str]:
    context = {
        ("disk", "usage_high"): (
            "The system drive or another monitored volume is near capacity.",
            "Free disk space, archive old files, or expand the affected volume.",
        ),
        ("memory", "usage_high"): (
            "A foreground workload, background service, or insufficient RAM is causing memory pressure.",
            "Review high-memory processes and consider a RAM upgrade for recurring pressure.",
        ),
        ("cpu", "temperature_high"): (
            "Sustained CPU load, blocked airflow, fan failure, or degraded thermal paste may be raising temperature.",
            "Inspect cooling, clean vents, verify fan operation, and reduce sustained CPU load.",
        ),
        ("network", "packet_loss_high"): (
            "Wireless signal quality, cabling, gateway congestion, or adapter issues may be dropping packets.",
            "Check adapter status, gateway reachability, cabling or Wi-Fi signal, and local network congestion.",
        ),
        ("network", "latency_high"): (
            "The endpoint is reachable but network response time is degraded.",
            "Test gateway latency, DNS response, Wi-Fi quality, and upstream network congestion.",
        ),
        ("disk", "smart_unhealthy"): (
            "SMART or disk health telemetry reported degradation or predicted failure.",
            "Back up data immediately and schedule disk replacement.",
        ),
        ("agent", "offline"): (
            "The monitoring agent has stopped checking in or the device cannot reach the API.",
            "Verify the device is powered on, network-connected, and that the scheduled agent task is running.",
        ),
    }
    return context.get(
        (str(issue.get("component")), str(issue.get("problem_type"))),
        (
            "Recent telemetry crossed a configured diagnostic threshold.",
            "Review current telemetry, recent changes, and device event history.",
        ),
    )


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def evidence_for_issue(issue: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = [
        {
            "component": issue.get("component"),
            "problemType": issue.get("problem_type"),
            "measuredValue": json_safe(issue.get("measured_value")),
            "thresholdValue": json_safe(issue.get("threshold_value")),
        }
    ]
    description = issue.get("description")
    if description:
        evidence.append({"summary": description})
    return evidence


def upsert_diagnostic_finding(
    client: Client,
    computer_id: str,
    issue: dict[str, Any],
    alert_id: str | None,
) -> str | None:
    finding_key = issue.get("alert_key") or f"{issue.get('component')}:{issue.get('problem_type')}"
    possible_cause, recommendation = issue_context(issue)
    existing = (
        client.table("diagnostic_findings")
        .select("id,occurrence_count,status")
        .eq("computer_id", computer_id)
        .eq("finding_key", finding_key)
        .in_("status", ["active", "acknowledged"])
        .limit(1)
        .execute()
        .data
        or []
    )
    payload = {
        "computer_id": computer_id,
        "alert_id": alert_id,
        "finding_key": finding_key,
        "finding_type": issue.get("problem_type") or "threshold",
        "component": issue.get("component") or "system",
        "severity": finding_severity(issue),
        "title": issue.get("title") or "Diagnostic finding",
        "description": issue.get("description") or "",
        "evidence": evidence_for_issue(issue),
        "possible_cause": possible_cause,
        "recommendation": recommendation,
        "last_detected_at": now_iso(),
        "recovery_count": 0,
        "status": "active",
        "updated_at": now_iso(),
    }
    if existing:
        payload["occurrence_count"] = int(existing[0].get("occurrence_count") or 1) + 1
        rows = client.table("diagnostic_findings").update(payload).eq("id", existing[0]["id"]).execute().data or []
        return rows[0].get("id") if rows else existing[0]["id"]

    payload["first_detected_at"] = payload["last_detected_at"]
    payload["occurrence_count"] = 1
    rows = client.table("diagnostic_findings").insert(payload).execute().data or []
    return rows[0].get("id") if rows else None


def sync_diagnostic_findings(
    client: Client,
    computer: dict[str, Any],
    issues: list[dict[str, Any]],
    alert_ids: dict[str, str | None],
) -> None:
    try:
        thresholds = load_thresholds(client)
        current_keys = set()
        for issue in issues:
            finding_key = issue.get("alert_key") or f"{issue.get('component')}:{issue.get('problem_type')}"
            current_keys.add(finding_key)
            upsert_diagnostic_finding(client, computer["id"], issue, alert_ids.get(finding_key))

        active = (
            client.table("diagnostic_findings")
            .select("id,finding_key,recovery_count")
            .eq("computer_id", computer["id"])
            .in_("status", ["active", "acknowledged"])
            .execute()
            .data
            or []
        )
        for finding in active:
            finding_key = finding.get("finding_key")
            if not finding_key or finding_key in current_keys:
                continue
            recovery_count = int(finding.get("recovery_count") or 0) + 1
            if recovery_count >= thresholds.alert_recovery_readings:
                client.table("diagnostic_findings").update(
                    {
                        "status": "resolved",
                        "resolved_at": now_iso(),
                        "recovery_count": recovery_count,
                        "updated_at": now_iso(),
                    }
                ).eq("id", finding["id"]).execute()
            else:
                client.table("diagnostic_findings").update(
                    {"recovery_count": recovery_count, "updated_at": now_iso()}
                ).eq("id", finding["id"]).execute()
    except Exception:
        logger.warning("Diagnostic finding sync failed for computer_id=%s", computer.get("id"), exc_info=True)
