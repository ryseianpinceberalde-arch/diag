import { Wind } from "lucide-react";

export function FanSpeedBadge({
  label,
  rpm,
  percent,
}: {
  label: string;
  rpm: number | null | undefined;
  percent?: number | null | undefined;
}) {
  const value = rpm ?? percent;
  if (value == null) return null;

  const unit = rpm == null && percent != null ? "%" : "RPM";
  const level = (rpm != null && rpm >= 2500) || (percent != null && percent >= 90) ? "warning" : "normal";
  const displayValue = `${Math.round(value)} ${unit}`;

  return (
    <div className={`temperature ${level}`} title={`${label}: ${displayValue}`}>
      <Wind size={16} />
      <div>
        <span>{label}</span>
        <strong>{displayValue}</strong>
      </div>
    </div>
  );
}
