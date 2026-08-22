from datetime import datetime
from ipaddress import IPv4Address, IPv6Address
from typing import Any, Literal
from pydantic import BaseModel, Field

Severity = Literal["low", "medium", "high", "critical"]
EventSeverity = Literal["info", "warning", "error", "critical"]


class AgentRegistration(BaseModel):
    device_id: str = Field(min_length=3, max_length=200)
    computer_name: str = Field(min_length=1, max_length=200)
    manufacturer: str | None = None
    model: str | None = None
    operating_system: str | None = None
    ip_address: IPv4Address | IPv6Address | None = None
    agent_version: str | None = None


class Computer(AgentRegistration):
    id: str
    status: str
    last_seen: datetime | None = None
    created_at: datetime


class DiagnosticReadingIn(BaseModel):
    device_id: str = Field(min_length=3, max_length=200)
    cpu_usage: float | None = Field(default=None, ge=0, le=100)
    cpu_temperature: float | None = None
    fan_speed_rpm: float | None = Field(default=None, ge=0)
    fan_speed_percent: float | None = Field(default=None, ge=0, le=100)
    ram_usage: float | None = Field(default=None, ge=0, le=100)
    disk_usage: float | None = Field(default=None, ge=0, le=100)
    disk_temperature: float | None = None
    disk_health: str | None = None
    battery_percentage: float | None = Field(default=None, ge=0, le=100)
    battery_health: float | None = Field(default=None, ge=0, le=100)
    network_latency: float | None = None
    packet_loss: float | None = Field(default=None, ge=0, le=100)
    uptime_seconds: int | None = Field(default=None, ge=0)
    recorded_at: datetime | None = None


class SystemEventIn(BaseModel):
    device_id: str = Field(min_length=3, max_length=200)
    event_type: str = Field(min_length=1, max_length=100)
    severity: EventSeverity
    source: str | None = None
    message: str = Field(min_length=1, max_length=2000)
    occurred_at: datetime | None = None


class AlertOut(BaseModel):
    id: str
    computer_id: str
    category: str
    severity: Severity
    title: str
    description: str
    status: str
    created_at: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None


class PredictionOut(BaseModel):
    id: str | None = None
    computer_id: str
    risk_score: int = Field(ge=0, le=100)
    risk_level: Literal["low", "medium", "high", "critical"]
    suspected_component: str
    reasons: list[str]
    recommended_action: str
    created_at: datetime | None = None


class PaginatedResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    limit: int
    offset: int
