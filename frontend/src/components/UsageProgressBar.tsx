export function UsageProgressBar({ label, value }: { label: string; value: number | null | undefined }) {
  const actual = Math.max(0, Math.min(100, value ?? 0));
  const level = actual >= 88 ? "critical" : actual >= 75 ? "warning" : "normal";

  return (
    <div className="usage">
      <div className="usage-label">
        <span>{label}</span>
        <strong>{value == null ? "-" : `${actual}%`}</strong>
      </div>
      <div className="usage-track">
        <span className={level} style={{ width: `${actual}%` }} />
      </div>
    </div>
  );
}
