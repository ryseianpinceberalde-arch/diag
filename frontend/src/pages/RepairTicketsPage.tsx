import { Download, RefreshCw, Wrench } from "lucide-react";
import { useEffect, useState } from "react";
import { LoadingBlock } from "../components/LoadingBlock";
import { StatusBadge } from "../components/StatusBadge";
import { apiFetch } from "../lib/api";
import { exportCsv } from "../lib/export";
import { RepairTicket } from "../types/models";

const statuses: RepairTicket["status"][] = ["open", "assigned", "in_progress", "waiting_for_parts", "resolved", "verified", "closed", "cancelled"];

export function RepairTicketsPage() {
  const [tickets, setTickets] = useState<RepairTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    setLoading(true);
    try {
      const data = await apiFetch<{ items: RepairTicket[] }>("/tickets");
      setTickets(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load repair tickets");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function update(id: string, status: RepairTicket["status"]) {
    setError("");
    try {
      await apiFetch(`/tickets/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update ticket");
    }
  }

  function exportTickets() {
    exportCsv("repair-tickets.csv", tickets.map((ticket) => ({
      ticket_number: ticket.ticket_number,
      computer: ticket.computers?.computer_name ?? ticket.computer_id,
      severity: ticket.severity,
      category: ticket.category,
      status: ticket.status,
      title: ticket.title,
      created_at: ticket.created_at
    })));
  }

  return (
    <div className="page">
      <header className="page-header row">
        <div>
          <h1>Repair Tickets</h1>
          <p>Track problems from diagnostic findings through repair, verification, and closure.</p>
        </div>
        <div className="header-actions">
          <button className="secondary" onClick={load}><RefreshCw size={16} /> Refresh</button>
          <button className="secondary" onClick={exportTickets} disabled={tickets.length === 0}><Download size={16} /> Export CSV</button>
        </div>
      </header>
      {error && <p className="error">{error}</p>}
      {loading ? <LoadingBlock /> : tickets.length === 0 ? <p className="empty">No repair tickets are open.</p> : (
        <div className="maintenance-board">
          {tickets.map((ticket) => (
            <article className="maintenance-card" key={ticket.id}>
              <div className="maintenance-icon"><Wrench size={18} /></div>
              <div>
                <strong>{ticket.ticket_number} - {ticket.title}</strong>
                <span>{ticket.computers?.computer_name ?? "Unknown computer"} - {ticket.category}</span>
                <p>{ticket.description}</p>
                {ticket.resolution && <p>Resolution: {ticket.resolution}</p>}
              </div>
              <div className="maintenance-meta">
                <StatusBadge value={ticket.severity} />
                <select value={ticket.status} onChange={(event) => update(ticket.id, event.target.value as RepairTicket["status"])} aria-label="Update repair ticket status">
                  {statuses.map((status) => <option key={status} value={status}>{status.replace(/_/g, " ")}</option>)}
                </select>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
