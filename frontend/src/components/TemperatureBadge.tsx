import { Thermometer } from "lucide-react";

function temperatureLevel(value: number | null | undefined) {
  if (value == null) return "unknown";
  if (value >= 85) return "critical";
  if (value >= 70) return "warning";
  return "normal";
}

export function TemperatureBadge({ label, value }: { label: string; value: number | null | undefined }) {
  const level = temperatureLevel(value);
  const displayValue = value == null ? "No sensor" : `${Math.round(value)} C`;

  return (
    <div className={`temperature ${level}`} title={`${label}: ${displayValue}`}>
      <Thermometer size={16} />
      <div>
        <span>{label}</span>
        <strong>{displayValue}</strong>
      </div>
    </div>
  );
}
