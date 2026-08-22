import { Thermometer } from "lucide-react";

function temperatureLevel(value: number) {
  if (value >= 85) return "critical";
  if (value >= 70) return "warning";
  return "normal";
}

export function TemperatureBadge({ label, value }: { label: string; value: number | null | undefined }) {
  if (value == null) return null;

  const level = temperatureLevel(value);
  const displayValue = `${Math.round(value)} C`;

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
