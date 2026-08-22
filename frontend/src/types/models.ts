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
  severity: RiskLevel;
  title: string;
  description: string;
  status: "active" | "acknowledged" | "resolved";
  created_at: string;
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
}
