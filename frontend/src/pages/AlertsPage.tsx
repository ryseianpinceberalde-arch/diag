import { AlertOctagon, Check, Download, RefreshCw, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { StatusBadge } from "../components/StatusBadge";
import { apiFetch } from "../lib/api";
import { exportCsv } from "../lib/export";
import { Alert } from "../types/models";

export function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ status: "", severity: "", component: "" });

  const load = useCallback(async () => {
    setError("");
    setLoading(true);
    try {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.set(key, value);
      });
      const data = await apiFetch<{ items: Alert[] }>(`/alerts${params.size ? `?${params}` : ""}`);
      setAlerts(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load alerts");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    load();
  }, [load]);

  async function update(id: string, action: "acknowledge" | "resolve") {
    if (!window.confirm(`Confirm ${action} for this alert?`)) return;
    try {
      await apiFetch(`/alerts/${id}/${action}`, { method: "PATCH" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${action} alert`);
    }
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
      <div className="toolbar">
        <select value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))} aria-label="Filter alert status">
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="resolved">Resolved</option>
        </select>
        <select value={filters.severity} onChange={(event) => setFilters((current) => ({ ...current, severity: event.target.value }))} aria-label="Filter alert severity">
          <option value="">All severities</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
        <input value={filters.component} onChange={(event) => setFilters((current) => ({ ...current, component: event.target.value }))} placeholder="Component" aria-label="Filter alert component" />
        <button className="secondary" onClick={load}><RefreshCw size={16} /> Retry</button>
      </div>
      {loading ? <p className="empty">Loading alerts...</p> : alerts.length === 0 ? <p className="empty">No alerts match the selected filters.</p> : (
        <div className="stack">
          {alerts.map((alert) => (
            <article className="alert-row" key={alert.id}>
              <div className="alert-icon"><AlertOctagon size={18} /></div>
              <div>
                <StatusBadge value={alert.severity} />
                <strong>{alert.title}</strong>
                <p>{alert.description}</p>
                <span>
                  {alert.computers?.computer_name ?? alert.computer_id} - {alert.status}
                  {alert.component ? ` - ${alert.component}` : ""}
                  {alert.occurrence_count ? ` - ${alert.occurrence_count}x` : ""}
                  {alert.measured_value != null && alert.threshold_value != null ? ` - ${alert.measured_value} / ${alert.threshold_value}` : ""}
                </span>
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
