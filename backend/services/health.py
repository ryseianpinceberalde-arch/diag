from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from services.settings import Thresholds
from services.status import parse_timestamp

HealthStatus = Literal["healthy", "warning", "critical", "offline"]


@dataclass
class HealthIssue:
    component: str
    problem_type: str
    severity: Literal["medium", "high", "critical"]
    title: str
    description: str
    measured_value: float | None
    threshold_value: float | None
    alert_key: str


STATUS_RANK: dict[HealthStatus, int] = {
    "healthy": 0,
    "warning": 1,
    "critical": 2,
    "offline": 3,
}


def issue_status(severity: str) -> HealthStatus:
    return "critical" if severity == "critical" else "warning"


def worst_status(statuses: list[HealthStatus]) -> HealthStatus:
    if not statuses:
        return "healthy"
    return max(statuses, key=lambda status: STATUS_RANK[status])


def threshold_issue(
    *,
    component: str,
    problem_type: str,
    value: float | None,
    warning: float,
    critical: float,
    unit: str,
    title: str,
    action: str,
) -> HealthIssue | None:
    if value is None:
        return None
    if value >= critical:
        severity: Literal["medium", "high", "critical"] = "critical"
        threshold = critical
    elif value >= warning:
        severity = "high"
        threshold = warning
    else:
        return None
    return HealthIssue(
        component=component,
        problem_type=problem_type,
        severity=severity,
        title=title,
        description=f"{component.title()} is {value:g}{unit}; threshold is {threshold:g}{unit}. {action}",
        measured_value=value,
        threshold_value=threshold,
        alert_key=f"{component}:{problem_type}",
    )


def evaluate_computer_health(
    computer: dict[str, Any],
    latest_reading: dict[str, Any] | None,
    thresholds: Thresholds,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    issues: list[HealthIssue] = []
    last_seen = parse_timestamp(computer.get("last_seen"))
    offline_seconds: int | None = None
    status: HealthStatus = "healthy"

    if not last_seen:
        offline_seconds = None
        status = "offline"
        issues.append(
            HealthIssue(
                component="agent",
                problem_type="offline",
                severity="critical",
                title="Computer agent is offline",
                description="No heartbeat has been received from this computer.",
                measured_value=None,
                threshold_value=thresholds.offline_after_seconds,
                alert_key="agent:offline",
            )
        )
    else:
        offline_seconds = max(0, int((now - last_seen).total_seconds()))
        if offline_seconds > thresholds.offline_after_seconds:
            status = "offline"
            issues.append(
                HealthIssue(
                    component="agent",
                    problem_type="offline",
                    severity="critical",
                    title="Computer agent is offline",
                    description=f"No heartbeat for {offline_seconds} seconds; threshold is {thresholds.offline_after_seconds} seconds.",
                    measured_value=float(offline_seconds),
                    threshold_value=float(thresholds.offline_after_seconds),
                    alert_key="agent:offline",
                )
            )

    latest = latest_reading or {}
    checks = [
        threshold_issue(
            component="disk",
            problem_type="usage_high",
            value=latest.get("disk_usage"),
            warning=thresholds.disk_warning_percent,
            critical=thresholds.disk_critical_percent,
            unit="%",
            title="Disk usage is high",
            action="Free storage, archive old data, or expand disk capacity.",
        ),
        threshold_issue(
            component="memory",
            problem_type="usage_high",
            value=latest.get("ram_usage"),
            warning=thresholds.ram_warning_percent,
            critical=thresholds.ram_critical_percent,
            unit="%",
            title="RAM usage is high",
            action="Review memory-heavy processes or plan a RAM upgrade.",
        ),
        threshold_issue(
            component="cpu",
            problem_type="temperature_high",
            value=latest.get("cpu_temperature"),
            warning=thresholds.cpu_temperature_warning_c,
            critical=thresholds.cpu_temperature_critical_c,
            unit="C",
            title="CPU temperature is high",
            action="Check cooling, clean vents, and reduce sustained load.",
        ),
        threshold_issue(
            component="network",
            problem_type="packet_loss_high",
            value=latest.get("packet_loss"),
            warning=thresholds.packet_loss_warning_percent,
            critical=thresholds.packet_loss_critical_percent,
            unit="%",
            title="Packet loss is high",
            action="Check gateway reachability, Wi-Fi quality, cabling, and adapter health.",
        ),
        threshold_issue(
            component="network",
            problem_type="latency_high",
            value=latest.get("network_latency"),
            warning=thresholds.latency_warning_ms,
            critical=thresholds.latency_critical_ms,
            unit="ms",
            title="Network latency is high",
            action="Check local network congestion, DNS, and gateway health.",
        ),
    ]
    issues.extend(issue for issue in checks if issue is not None)

    disk_health = str(latest.get("disk_health") or "").lower()
    if disk_health in {"warning", "fail", "failed", "bad", "critical"}:
        issues.append(
            HealthIssue(
                component="disk",
                problem_type="smart_unhealthy",
                severity="critical",
                title="SMART disk health is unhealthy",
                description=f"SMART disk health reported {disk_health}. Back up data and schedule disk replacement.",
                measured_value=None,
                threshold_value=None,
                alert_key="disk:smart_unhealthy",
            )
        )

    if status != "offline":
        status = worst_status([issue_status(issue.severity) for issue in issues])

    return {
        "status": status,
        "offline_seconds": offline_seconds,
        "issues": [asdict(issue) for issue in issues],
        "latest_reading": latest_reading,
    }
