export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface DiagnosticReading {
  id: number;
  cpu_usage: number | null;
  cpu_temperature: number | null;
  fan_speed_rpm: number | null;
  fan_speed_percent: number | null;
  ram_usage: number | null;
  disk_usage: number | null;
  disk_temperature: number | null;
  disk_health: string | null;
  battery_percentage: number | null;
  battery_health: number | null;
  network_latency: number | null;
  packet_loss: number | null;
  uptime_seconds: number | null;
  recorded_at: string;
}

export interface Prediction {
  id: string;
  computer_id: string;
  risk_score: number;
  risk_level: RiskLevel;
  suspected_component: string;
  reasons: string[];
  recommended_action: string;
  created_at: string;
}

export interface Alert {
  id: string;
  computer_id: string;
  category: string;
  component: string | null;
  alert_key: string | null;
  severity: RiskLevel;
  title: string;
  description: string;
  status: "active" | "acknowledged" | "resolved";
  created_at: string;
  first_detected_at: string | null;
  last_detected_at: string | null;
  occurrence_count: number;
  measured_value: number | null;
  threshold_value: number | null;
  acknowledged_at: string | null;
  resolved_at: string | null;
  computers?: { computer_name: string; device_id: string };
}

export interface Computer {
  id: string;
  device_id: string;
  computer_name: string;
  manufacturer: string | null;
  model: string | null;
  operating_system: string | null;
  ip_address: string | null;
  agent_version: string | null;
  status: string;
  last_seen: string | null;
  created_at: string;
  latest_reading?: DiagnosticReading | null;
  latest_prediction?: Prediction | null;
  health_level?: string;
  health_issues?: Array<{ title: string; description: string; severity: string; component: string }>;
  tags?: string[];
  notes?: string | null;
}

export interface AppSettings {
  offline_after_seconds: number;
  agent_reporting_interval_seconds: number;
  disk_warning_percent: number;
  disk_critical_percent: number;
  ram_warning_percent: number;
  ram_critical_percent: number;
  cpu_temperature_warning_c: number;
  cpu_temperature_critical_c: number;
  packet_loss_warning_percent: number;
  packet_loss_critical_percent: number;
  latency_warning_ms: number;
  latency_critical_ms: number;
  risk_warning_score: number;
  risk_critical_score: number;
  alert_recovery_readings: number;
  data_retention_days: number;
  notifications_enabled: boolean;
  notification_recipients: string[];
}

export interface AgentCommand {
  id: string;
  computer_id: string;
  device_id: string;
  action: "system_info" | "process_list" | "services_list" | "disk_summary" | "network_test" | "restart" | "shutdown" | "uninstall_agent";
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  requested_at: string;
  picked_up_at: string | null;
  completed_at: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
}

export interface Profile {
  id: string;
  email: string | null;
  full_name: string | null;
  role: "administrator" | "technician" | "viewer";
  is_active: boolean;
  created_at: string;
}

export interface MaintenanceTicket {
  id: string;
  computer_id: string;
  component: string;
  problem_type: string;
  title: string;
  description: string;
  priority: RiskLevel;
  status: "pending" | "in_progress" | "completed" | "cancelled";
  assigned_technician: string | null;
  due_date: string | null;
  technician_notes: string | null;
  resolution_description: string | null;
  created_at: string;
  completed_at: string | null;
  computers?: { computer_name: string; device_id: string };
}
