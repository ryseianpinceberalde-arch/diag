from datetime import date, datetime, timedelta, timezone
from ipaddress import IPv4Address, IPv6Address
from typing import Any, Literal
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

Severity = Literal["low", "medium", "high", "critical"]
EventSeverity = Literal["info", "warning", "error", "critical"]


class AgentRegistration(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    device_id: str = Field(min_length=3, max_length=200, validation_alias=AliasChoices("device_id", "deviceId"))
    computer_name: str = Field(min_length=1, max_length=200, validation_alias=AliasChoices("computer_name", "hostname"))
    display_name: str | None = None
    asset_tag: str | None = None
    device_type: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = Field(default=None, validation_alias=AliasChoices("serial_number", "serialNumber"))
    operating_system: str | None = Field(default=None, validation_alias=AliasChoices("operating_system", "operatingSystem"))
    os_version: str | None = Field(default=None, validation_alias=AliasChoices("os_version", "osVersion"))
    architecture: str | None = None
    department_id: str | None = None
    location_id: str | None = None
    assigned_user_id: str | None = None
    owner_name: str | None = None
    purchase_date: date | None = None
    warranty_start_date: date | None = None
    warranty_end_date: date | None = None
    ip_address: IPv4Address | IPv6Address | None = None
    agent_version: str | None = Field(default=None, validation_alias=AliasChoices("agent_version", "agentVersion"))
    registration_code: str | None = Field(default=None, min_length=1, max_length=200, validation_alias=AliasChoices("registration_code", "registrationCode"))


class AgentTelemetry(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    device_id: str = Field(min_length=3, max_length=200, validation_alias=AliasChoices("device_id", "deviceId"))
    agent_version: str | None = Field(default=None, validation_alias=AliasChoices("agent_version", "agentVersion"))
    timestamp: datetime | None = Field(default=None, validation_alias=AliasChoices("timestamp", "recordedAt"))
    last_heartbeat: datetime | None = None
    agent_status: str | None = None
    system: dict[str, Any] = Field(default_factory=dict)
    cpu: dict[str, Any] = Field(default_factory=dict)
    memory: dict[str, Any] = Field(default_factory=dict)
    storage: list[dict[str, Any]] = Field(default_factory=list)
    network: list[dict[str, Any]] = Field(default_factory=list)
    gpu: list[dict[str, Any]] = Field(default_factory=list)
    battery: dict[str, Any] | None = None
    temperature: dict[str, Any] = Field(default_factory=dict)
    processes: list[dict[str, Any]] = Field(default_factory=list, max_length=25)
    hardware_health: dict[str, Any] = Field(default_factory=dict)
    capabilities: list[str] = Field(default_factory=list, max_length=32)

    @model_validator(mode="before")
    @classmethod
    def normalize_wire_format(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if "topProcesses" in normalized and "processes" not in normalized:
            normalized["processes"] = normalized["topProcesses"]
        for section, aliases in {
            "cpu": {"usagePercent": "usage_percent", "physicalCores": "physical_cores", "logicalCores": "logical_processors", "clockMHz": "clock_speed_mhz", "temperatureC": "temperature_c"},
            "memory": {"totalBytes": "total_bytes", "usedBytes": "used_bytes", "availableBytes": "available_bytes", "usagePercent": "usage_percent"},
        }.items():
            if isinstance(normalized.get(section), dict):
                normalized[section] = {aliases.get(key, key): item for key, item in normalized[section].items()}
        return normalized

    @model_validator(mode="after")
    def validate_percentages(self) -> "AgentTelemetry":
        if self.timestamp and self.timestamp > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("timestamp cannot be more than five minutes in the future")
        values = [
            ("cpu.usage_percent", self.cpu.get("usage_percent")),
            ("memory.usage_percent", self.memory.get("usage_percent")),
        ]
        values.extend(
            (f"storage[{index}].usage_percent", disk.get("usage_percent"))
            for index, disk in enumerate(self.storage)
        )
        if self.battery is not None:
            values.append(("battery.percentage", self.battery.get("percentage")))
        for name, value in values:
            if value is None:
                continue
            try:
                numeric = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{name} must be numeric") from exc
            if not 0 <= numeric <= 100:
                raise ValueError(f"{name} must be between 0 and 100")
        if any(any("command" in key or "argument" in key for key in process) for process in self.processes):
            raise ValueError("process command-line data is not accepted")
        temperature = self.temperature
        if temperature.get("available") is False and temperature.get("temperatureC") is not None:
            raise ValueError("temperatureC must be null when temperature is unavailable")
        return self


class AgentHeartbeat(AgentTelemetry):
    """Backward-compatible heartbeat payload; telemetry uses the same contract."""
    pass


class Computer(AgentRegistration):
    id: str
    status: str
    last_seen: datetime | None = None
    created_at: datetime


class ComputerUpdate(BaseModel):
    display_name: str | None = None
    asset_tag: str | None = None
    device_type: str | None = None
    department_id: str | None = None
    location_id: str | None = None
    assigned_user_id: str | None = None
    owner_name: str | None = None
    purchase_date: datetime | None = None
    warranty_start_date: datetime | None = None
    warranty_end_date: datetime | None = None
    tags: list[str] | None = None
    notes: str | None = None


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
