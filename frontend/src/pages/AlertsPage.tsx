import { AlertOctagon, Check, Download, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { StatusBadge } from "../components/StatusBadge";
import { apiFetch } from "../lib/api";
import { exportCsv } from "../lib/export";
import { Alert } from "../types/models";

export function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [error, setError] = useState("");

  async function load() {
    const data = await apiFetch<{ items: Alert[] }>("/alerts");
    setAlerts(data.items);
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  async function update(id: string, action: "acknowledge" | "resolve") {
    if (!window.confirm(`Confirm ${action} for this alert?`)) return;
    await apiFetch(`/alerts/${id}/${action}`, { method: "PATCH" });
    await load();
  }

  function exportAlerts() {
    exportCsv("alerts.csv", alerts.map((alert) => ({
      title: alert.title,
      computer: alert.computers?.computer_name ?? alert.computer_id,
      category: alert.category,
      severity: alert.severity,
      status: alert.status,
      description: alert.description,
      created_at: alert.created_at
    })));
  }

  return (
    <div className="page">
      <header className="page-header row">
        <div>
          <h1>System Alert Center</h1>
          <p>Hardware anomalies, thermal breaches, prediction alerts and Windows event violations.</p>
        </div>
        <button className="secondary" onClick={exportAlerts} disabled={alerts.length === 0}><Download size={16} /> Export CSV</button>
      </header>
      {error && <p className="error">{error}</p>}
      {alerts.length === 0 ? <p className="empty">No alerts are active.</p> : (
        <div className="stack">
          {alerts.map((alert) => (
            <article className="alert-row" key={alert.id}>
              <div className="alert-icon"><AlertOctagon size={18} /></div>
              <div>
                <StatusBadge value={alert.severity} />
                <strong>{alert.title}</strong>
                <p>{alert.description}</p>
                <span>{alert.computers?.computer_name ?? alert.computer_id} - {alert.status}</span>
              </div>
              <button onClick={() => update(alert.id, "acknowledge")} disabled={alert.status === "resolved"} title="Acknowledge alert" aria-label="Acknowledge alert"><Check size={16} /></button>
              <button onClick={() => update(alert.id, "resolve")} title="Resolve alert" aria-label="Resolve alert"><ShieldCheck size={16} /></button>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
