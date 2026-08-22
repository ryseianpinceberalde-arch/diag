export function RiskScoreIndicator({ score, compact = false }: { score: number; compact?: boolean }) {
  const clamped = Math.max(0, Math.min(100, score));
  const level = clamped >= 80 ? "critical" : clamped >= 60 ? "high" : clamped >= 35 ? "medium" : "low";

  if (compact) {
    return (
      <span className={`risk-pill ${level}`}>
        {clamped}%
      </span>
    );
  }

  return (
    <div className="risk-meter">
      <div className="risk-track">
        <span className={level} style={{ width: `${clamped}%` }} />
      </div>
      <strong>{clamped}%</strong>
      <em>{level}</em>
    </div>
  );
}
