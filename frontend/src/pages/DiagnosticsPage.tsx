import { AlertTriangle, ClipboardList, RefreshCw, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { LoadingBlock } from "../components/LoadingBlock";
import { StatusBadge } from "../components/StatusBadge";
import { apiFetch } from "../lib/api";
import { DiagnosticFinding } from "../types/models";

export function DiagnosticsPage() {
  const [findings, setFindings] = useState<DiagnosticFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [filters, setFilters] = useState({ status: "active", severity: "", component: "" });

  const load = useCallback(async () => {
    setError("");
    setLoading(true);
    try {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.set(key, value);
      });
      const data = await apiFetch<{ items: DiagnosticFinding[] }>(`/diagnostics${params.size ? `?${params}` : ""}`);
      setFindings(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load diagnostic findings");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    load();
  }, [load]);

  async function updateFinding(id: string, status: DiagnosticFinding["status"]) {
    setError("");
    setNotice("");
    try {
      await apiFetch(`/diagnostics/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update finding");
    }
  }

  async function createTicket(id: string) {
    setError("");
    setNotice("");
    try {
      const data = await apiFetch<{ created: boolean; ticket: { ticket_number: string } }>(`/diagnostics/${id}/ticket`, {
        method: "POST",
        body: JSON.stringify({})
      });
      setNotice(data.created ? `Created repair ticket ${data.ticket.ticket_number}.` : `Existing repair ticket ${data.ticket.ticket_number} is already open.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create repair ticket");
    }
  }

  return (
    <div className="page">
      <header className="page-header row">
        <div>
          <h1>Diagnostics</h1>
          <p>Active findings generated from telemetry thresholds and agent connectivity checks.</p>
        </div>
        <button className="secondary" onClick={load}><RefreshCw size={16} /> Refresh</button>
      </header>
      {error && <p className="error">{error}</p>}
      {notice && <p className="success">{notice}</p>}
      <div className="toolbar">
        <select value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))} aria-label="Filter finding status">
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="resolved">Resolved</option>
          <option value="ignored">Ignored</option>
        </select>
        <select value={filters.severity} onChange={(event) => setFilters((current) => ({ ...current, severity: event.target.value }))} aria-label="Filter finding severity">
          <option value="">All severities</option>
          <option value="warning">Warning</option>
          <option value="critical">Critical</option>
        </select>
        <input value={filters.component} onChange={(event) => setFilters((current) => ({ ...current, component: event.target.value }))} placeholder="Component" aria-label="Filter finding component" />
      </div>
      {loading ? <LoadingBlock /> : findings.length === 0 ? <p className="empty">No diagnostic findings match the selected filters.</p> : (
        <div className="stack">
          {findings.map((finding) => (
            <article className="alert-row" key={finding.id}>
              <div className="alert-icon"><AlertTriangle size={18} /></div>
              <div>
                <StatusBadge value={finding.severity} />
                <strong>{finding.title}</strong>
                <p>{finding.description}</p>
                {finding.possible_cause && <p>Possible cause: {finding.possible_cause}</p>}
                {finding.recommendation && <p>Recommendation: {finding.recommendation}</p>}
                <span>
                  {finding.computers?.computer_name ?? finding.computer_id} - {finding.component} - {finding.status} - {finding.occurrence_count}x
                </span>
              </div>
              <button onClick={() => createTicket(finding.id)} title="Create ticket" aria-label="Create ticket"><ClipboardList size={16} /></button>
              <button onClick={() => updateFinding(finding.id, "acknowledged")} disabled={finding.status === "resolved"} title="Acknowledge finding" aria-label="Acknowledge finding"><ShieldCheck size={16} /></button>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
