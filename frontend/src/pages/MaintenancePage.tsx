import { CalendarClock, RefreshCw, Wrench } from "lucide-react";
import { useEffect, useState } from "react";
import { LoadingBlock } from "../components/LoadingBlock";
import { StatusBadge } from "../components/StatusBadge";
import { apiFetch } from "../lib/api";
import { MaintenanceTicket } from "../types/models";

export function MaintenancePage() {
  const [items, setItems] = useState<MaintenanceTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    setLoading(true);
    try {
      const data = await apiFetch<{ items: MaintenanceTicket[] }>("/maintenance");
      setItems(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load maintenance tickets");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function update(id: string, status: MaintenanceTicket["status"]) {
    try {
      await apiFetch(`/maintenance/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update ticket");
    }
  }

  return (
    <div className="page">
      <header className="page-header row">
        <div>
          <h1>Preventive Maintenance</h1>
          <p>Deduplicated maintenance tickets generated from active threshold problems.</p>
        </div>
        <button className="secondary" onClick={load}><RefreshCw size={16} /> Refresh</button>
      </header>
      {error && <p className="error">{error}</p>}
      {loading ? <LoadingBlock /> : items.length === 0 ? <p className="empty">No maintenance tickets are queued.</p> : (
        <div className="maintenance-board">
          {items.map((item) => (
            <article className="maintenance-card" key={item.id}>
              <div className="maintenance-icon"><Wrench size={18} /></div>
              <div>
                <strong>{item.computers?.computer_name ?? "Unknown computer"}</strong>
                <span>{item.component} - {item.status}</span>
                <p>{item.description}</p>
                {item.technician_notes && <p>{item.technician_notes}</p>}
              </div>
              <div className="maintenance-meta">
                <StatusBadge value={item.priority} />
                <span><CalendarClock size={14} /> {item.due_date ? new Date(item.due_date).toLocaleDateString() : "No due date"}</span>
                <select value={item.status} onChange={(event) => update(item.id, event.target.value as MaintenanceTicket["status"])} aria-label="Update ticket status">
                  <option value="pending">Pending</option>
                  <option value="in_progress">In progress</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
