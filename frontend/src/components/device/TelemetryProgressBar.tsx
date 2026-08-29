import { clampPercent, formatPercent } from "../../lib/formatters";

export function TelemetryProgressBar({
  value,
  warning,
  critical,
  label = "Utilization",
  inverse = false,
}: {
  value: unknown;
  warning: number;
  critical: number;
  label?: string;
  inverse?: boolean;
}) {
  const actual = clampPercent(value);
  const level = actual === null
    ? "unavailable"
    : inverse
      ? actual <= critical ? "critical" : actual <= warning ? "warning" : "normal"
      : actual >= critical ? "critical" : actual >= warning ? "warning" : "normal";

  return (
    <div className="device-progress">
      <div className="device-progress-label">
        <span>{label}</span>
        <strong>{formatPercent(actual)}</strong>
      </div>
      <div className="device-progress-track" aria-label={`${label}: ${formatPercent(actual)}`}>
        <span className={level} style={{ width: `${actual ?? 0}%` }} />
      </div>
    </div>
  );
}
