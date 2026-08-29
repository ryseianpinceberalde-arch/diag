import { Activity, ClipboardList, Cpu, HardDrive, Network, ScrollText, Wrench } from "lucide-react";
import { MonitoringTab } from "./types";

const tabs: Array<{ id: MonitoringTab; label: string; icon: typeof Activity; countKey?: "processes" | "findings" | "tickets" | "maintenance" }> = [
  { id: "telemetry", label: "Live Telemetry & Sensors", icon: Activity },
  { id: "wifi", label: "Wi-Fi Diagnostics", icon: Network },
  { id: "hardware", label: "Hardware Specifications", icon: Cpu },
  { id: "processes", label: "Active Processes", icon: HardDrive, countKey: "processes" },
  { id: "findings", label: "Detected Findings", icon: ClipboardList, countKey: "findings" },
  { id: "tickets", label: "Repair Tickets", icon: Wrench, countKey: "tickets" },
  { id: "maintenance", label: "Maintenance Log", icon: ScrollText, countKey: "maintenance" },
];

export function MonitoringTabs({ active, counts, onChange }: { active: MonitoringTab; counts: Record<string, number>; onChange: (tab: MonitoringTab) => void }) {
  return (
    <nav className="monitoring-tabs" aria-label="Device monitoring sections">
      {tabs.map(({ id, label, icon: Icon, countKey }) => (
        <button key={id} className={active === id ? "active" : ""} onClick={() => onChange(id)}>
          <Icon size={15} />
          {label}
          {countKey && <span>{counts[countKey] ?? 0}</span>}
        </button>
      ))}
    </nav>
  );
}
