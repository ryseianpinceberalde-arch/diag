import { Activity, Clock3, Gauge, Laptop, MapPin, MonitorCog, Network, UserRound } from "lucide-react";
import { asNumber, asText, formatDuration, formatRelativeTime, UnknownRecord } from "../../lib/formatters";
import { Computer, DiagnosticReading } from "../../types/models";
import { AssignedUser } from "./types";

function SummaryCard({ icon: Icon, label, value, detail, tone }: { icon: typeof Gauge; label: string; value: string; detail?: string; tone?: string }) {
  return (
    <article className={`device-summary-card ${tone || ""}`}>
      <span className="device-summary-icon"><Icon size={18} /></span>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        {detail && <small>{detail}</small>}
      </div>
    </article>
  );
}

export function DeviceSummaryCards({
  computer,
  reading,
  assignedUser,
  system,
  primaryNetwork,
}: {
  computer: Computer;
  reading: DiagnosticReading | null;
  assignedUser: AssignedUser | null;
  system: UnknownRecord;
  primaryNetwork: UnknownRecord;
}) {
  const health = computer.health_score;
  const score = asNumber(health?.score);
  const healthTone = score === null ? "neutral" : score < 40 ? "critical" : score < 65 ? "poor" : score < 80 ? "warning" : "healthy";
  const os = [computer.operating_system, computer.os_version || asText(system.os_version), computer.windows_build ? `Build ${computer.windows_build}` : null].filter(Boolean).join(" • ");
  const heartbeat = computer.last_heartbeat || computer.last_seen;
  const uptime = reading?.uptime_seconds ?? asNumber(system.uptime_seconds);

  return (
    <div className="device-summary-grid">
      <SummaryCard icon={Gauge} label="Health Score" value={score === null ? "Not available" : `${score}/100`} detail={health?.label || "Unknown"} tone={healthTone} />
      <SummaryCard icon={UserRound} label="Assigned User" value={assignedUser?.full_name || computer.owner_name || "Unassigned"} />
      <SummaryCard icon={MonitorCog} label="Operating System" value={os || "Not reported"} />
      <SummaryCard icon={Network} label="IP Address" value={computer.ip_address || asText(primaryNetwork.ipv4) || "Not reported"} />
      <SummaryCard icon={MapPin} label="MAC Address" value={asText(primaryNetwork.mac_address) || "Not reported"} />
      <SummaryCard icon={Clock3} label="Last Heartbeat" value={formatRelativeTime(heartbeat)} detail={heartbeat ? new Date(heartbeat).toLocaleString() : "No heartbeat received"} />
      <SummaryCard icon={Activity} label="Uptime" value={formatDuration(uptime)} />
      <SummaryCard icon={computer.device_type === "laptop" ? Laptop : MonitorCog} label="Device Type" value={computer.device_type || asText(system.device_type) || "Not reported"} />
    </div>
  );
}
