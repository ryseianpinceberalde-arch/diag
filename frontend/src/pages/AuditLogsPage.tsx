import { RefreshCw, ScrollText } from "lucide-react";
import { useEffect, useState } from "react";
import { LoadingBlock } from "../components/LoadingBlock";
import { apiFetch } from "../lib/api";
import { AuditLog } from "../types/models";

export function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    setLoading(true);
    try {
      const data = await apiFetch<{ items: AuditLog[] }>("/audit-logs");
      setLogs(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="page">
      <header className="page-header row">
        <div>
          <h1>Audit Logs</h1>
          <p>Administrative changes and automated workflow events.</p>
        </div>
        <button className="secondary" onClick={load}><RefreshCw size={16} /> Refresh</button>
      </header>
      {error && <p className="error">{error}</p>}
      {loading ? <LoadingBlock /> : logs.length === 0 ? <p className="empty">No audit events are available.</p> : (
        <div className="stack">
          {logs.map((log) => (
            <article className="report-row" key={log.id}>
              <div className="report-icon"><ScrollText size={18} /></div>
              <div>
                <strong>{log.action}</strong>
                <p>{log.target_type ?? "system"} {log.target_id ?? ""}</p>
                <span>{new Date(log.created_at).toLocaleString()}</span>
              </div>
              <code className="mono">{log.actor_id ?? "system"}</code>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
