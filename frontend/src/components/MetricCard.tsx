import { KeyboardEvent } from "react";
import { LucideIcon } from "lucide-react";

export function MetricCard({ label, value, icon: Icon, onClick }: { label: string; value: string | number; icon: LucideIcon; onClick?: () => void }) {
  function onKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (!onClick) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onClick();
    }
  }

  return (
    <section className={`metric ${onClick ? "clickable" : ""}`} role={onClick ? "button" : undefined} tabIndex={onClick ? 0 : undefined} onClick={onClick} onKeyDown={onKeyDown}>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <div className="metric-icon">
        <Icon size={20} />
      </div>
    </section>
  );
}
