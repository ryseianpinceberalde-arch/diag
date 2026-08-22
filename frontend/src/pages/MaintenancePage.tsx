import { CalendarClock, Wrench } from "lucide-react";
import { useEffect, useState } from "react";
import { LoadingBlock } from "../components/LoadingBlock";
import { StatusBadge } from "../components/StatusBadge";
import { apiFetch } from "../lib/api";

interface ReportItem {
  computer: { computer_name: string; device_id: string } | null;
  risk_level: string;
  risk_score: number;
  component: string;
  recommendation: string;
  created_at: string;
}

export function MaintenancePage() {
  const [items, setItems] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch<{ items: ReportItem[] }>("/reports/maintenance")
      .then((data) => setItems(data.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page">
      <header className="page-header">
        <h1>Preventive Maintenance</h1>
        <p>Prioritized actions generated from prediction history.</p>
      </header>
      {error && <p className="error">{error}</p>}
      {loading ? <LoadingBlock /> : items.length === 0 ? <p className="empty">No maintenance actions are queued.</p> : (
        <div className="maintenance-board">
          {items.map((item, index) => (
            <article className="maintenance-card" key={`${item.created_at}-${index}`}>
              <div className="maintenance-icon"><Wrench size={18} /></div>
              <div>
                <strong>{item.computer?.computer_name ?? "Unknown computer"}</strong>
                <span>{item.component} · score {item.risk_score}</span>
                <p>{item.recommendation}</p>
              </div>
              <div className="maintenance-meta">
                <StatusBadge value={item.risk_level} />
                <span><CalendarClock size={14} /> {new Date(item.created_at).toLocaleDateString()}</span>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
