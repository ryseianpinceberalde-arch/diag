import { Alert, AppSettings, Computer, DiagnosticFinding, DiagnosticReading, MaintenanceRecord, Prediction, RepairTicket } from "../../types/models";
import { UnknownRecord } from "../../lib/formatters";

export interface DevicePermissions {
  update_agent: boolean;
  remote_support: boolean;
  log_maintenance: boolean;
  create_ticket: boolean;
  delete_device: boolean;
  edit_device: boolean;
  run_analysis: boolean;
  download_report: boolean;
}

export interface AssignedUser {
  id: string;
  full_name: string | null;
}

export interface DeviceDetailResponse {
  computer: Computer;
  latest_reading: DiagnosticReading | null;
  alerts: Alert[];
  latest_prediction: Prediction | null;
  assigned_user: AssignedUser | null;
  permissions: DevicePermissions;
}

export interface DeviceHardware {
  system: UnknownRecord;
  cpu: UnknownRecord;
  memory: UnknownRecord;
  storage: UnknownRecord[];
  gpu: UnknownRecord[];
  battery: UnknownRecord | null;
}

export interface DeviceOperationalData {
  hardware: DeviceHardware;
  network: UnknownRecord[];
  processes: UnknownRecord[];
  findings: DiagnosticFinding[];
  tickets: RepairTicket[];
  maintenance: MaintenanceRecord[];
}

export type MonitoringTab = "telemetry" | "wifi" | "hardware" | "processes" | "findings" | "tickets" | "maintenance";

export const DEFAULT_PERMISSIONS: DevicePermissions = {
  update_agent: false,
  remote_support: false,
  log_maintenance: false,
  create_ticket: false,
  delete_device: false,
  edit_device: false,
  run_analysis: false,
  download_report: true,
};

export const DEFAULT_SETTINGS: AppSettings = {
  offline_after_seconds: 120,
  agent_reporting_interval_seconds: 10,
  disk_warning_percent: 85,
  disk_critical_percent: 95,
  ram_warning_percent: 85,
  ram_critical_percent: 95,
  cpu_temperature_warning_c: 80,
  cpu_temperature_critical_c: 90,
  packet_loss_warning_percent: 5,
  packet_loss_critical_percent: 10,
  latency_warning_ms: 200,
  latency_critical_ms: 500,
  risk_warning_score: 35,
  risk_critical_score: 75,
  alert_recovery_readings: 2,
  data_retention_days: 365,
  notifications_enabled: false,
  notification_recipients: [],
};
