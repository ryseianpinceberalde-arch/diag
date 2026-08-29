export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface DiagnosticReading {
  id: number;
  cpu_usage: number | null;
  cpu_temperature: number | null;
  gpu_usage?: number | null;
  gpu_temperature?: number | null;
  gpu_memory_usage?: number | null;
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
  os_version?: string | null;
  windows_build?: string | null;
  architecture?: string | null;
  serial_number?: string | null;
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
  display_name?: string | null;
  asset_tag?: string | null;
  device_type?: string | null;
  department_id?: string | null;
  location_id?: string | null;
  assigned_user_id?: string | null;
  owner_name?: string | null;
  agent_status?: string | null;
  last_heartbeat?: string | null;
  capabilities?: string[];
  health_score?: { score: number | null; label: string; factors: Record<string, number> };
  agent_inventory?: {
    system?: Record<string, unknown>;
    cpu?: Record<string, unknown>;
    memory?: Record<string, unknown>;
    storage?: Array<Record<string, unknown>>;
    network?: Array<Record<string, unknown>>;
    gpu?: Array<Record<string, unknown>>;
    battery?: Record<string, unknown>;
    temperature?: Record<string, unknown>;
    processes?: Array<Record<string, unknown>>;
    hardware_health?: Record<string, unknown>;
  };
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
  role: "super_admin" | "it_admin" | "administrator" | "technician" | "department_user" | "viewer";
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

export interface DiagnosticFinding {
  id: string;
  computer_id: string;
  alert_id: string | null;
  finding_key: string;
  finding_type: string;
  component: string;
  severity: "info" | "warning" | "critical";
  title: string;
  description: string;
  evidence: Array<Record<string, unknown>>;
  possible_cause: string | null;
  recommendation: string | null;
  first_detected_at: string;
  last_detected_at: string;
  occurrence_count: number;
  status: "active" | "acknowledged" | "resolved" | "ignored";
  resolved_at: string | null;
  computers?: { computer_name: string; device_id: string; department_id?: string | null; location_id?: string | null };
}

export interface RepairTicket {
  id: string;
  ticket_number: string;
  computer_id: string;
  diagnostic_finding_id: string | null;
  reported_by: string | null;
  assigned_technician_id: string | null;
  severity: "info" | "warning" | "critical" | "low" | "medium" | "high";
  category: string;
  title: string;
  description: string;
  status: "open" | "assigned" | "in_progress" | "waiting_for_parts" | "resolved" | "verified" | "closed" | "cancelled";
  resolution: string | null;
  verification_notes: string | null;
  resolved_at: string | null;
  verified_at: string | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
  computers?: { computer_name: string; device_id: string };
  diagnostic_findings?: { title: string; component: string; severity: string } | null;
  assigned_technician?: { id: string; full_name: string | null } | null;
}

export interface MaintenanceRecord {
  id: string;
  computer_id: string;
  ticket_id: string | null;
  maintenance_type: "preventive" | "corrective" | "inspection" | "cleaning" | "software" | "hardware";
  problem_description: string | null;
  actions_taken: string | null;
  parts_replaced: string | null;
  technician_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  status: "scheduled" | "in_progress" | "completed" | "cancelled";
  notes: string | null;
  created_at: string;
  updated_at: string;
  computers?: { computer_name: string; device_id: string };
  repair_tickets?: { ticket_number: string; title: string } | null;
  technician?: { id: string; full_name: string | null } | null;
}

export interface Department {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface Location {
  id: string;
  name: string;
  building: string | null;
  room: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditLog {
  id: number;
  actor_id: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}
