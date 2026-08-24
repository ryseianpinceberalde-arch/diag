import { Download, FileText, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { RiskScoreIndicator } from "../components/RiskScoreIndicator";
import { StatusBadge } from "../components/StatusBadge";
import { apiFetch } from "../lib/api";
import { exportCsv } from "../lib/export";

interface ReportItem {
  computer: { computer_name: string; device_id: string } | null;
  risk_level: string;
  risk_score: number | null;
  component: string;
  recommendation: string;
  created_at: string;
}

export function ReportsPage() {
  const [items, setItems] = useState<ReportItem[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setError("");
    setLoading(true);
    try {
      const data = await apiFetch<{ items: ReportItem[] }>("/reports/maintenance");
      setItems(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load report");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function exportReports() {
    exportCsv("maintenance-reports.csv", items.map((item) => ({
      computer: item.computer?.computer_name ?? "Unknown computer",
      device_id: item.computer?.device_id,
      component: item.component,
      risk_level: item.risk_level,
      risk_score: item.risk_score,
      recommendation: item.recommendation,
      created_at: item.created_at
    })));
  }

  return (
    <div className="page">
      <header className="page-header row">
        <div>
          <h1>Auditing & System Reports</h1>
          <p>Generate, preview and export enterprise health and inventory documents.</p>
        </div>
        <div className="header-actions">
          <button className="secondary" onClick={load}><RefreshCw size={16} /> Retry</button>
          <button className="secondary" onClick={exportReports} disabled={items.length === 0}><Download size={16} /> Export CSV</button>
        </div>
      </header>
      {error && <p className="error">{error}</p>}
      {loading ? <p className="empty">Loading report...</p> : items.length === 0 ? <p className="empty">No maintenance reports are available.</p> : (
        <div className="stack">
          {items.map((item, index) => (
            <article className="report-row" key={`${item.created_at}-${index}`}>
              <div className="report-icon"><FileText size={18} /></div>
              <div>
                <StatusBadge value={item.risk_level} />
                <strong>{item.computer?.computer_name ?? "Unknown computer"} - {item.component}</strong>
                <p>{item.recommendation}</p>
              </div>
              {item.risk_score != null && <RiskScoreIndicator compact score={item.risk_score} />}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
