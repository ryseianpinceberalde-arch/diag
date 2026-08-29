import { Plus, Wrench } from "lucide-react";
import { formatDateTime } from "../../lib/formatters";
import { RepairTicket } from "../../types/models";
import { StatusBadge } from "../StatusBadge";

export function RepairTicketList({ tickets, canCreate, onCreate }: { tickets: RepairTicket[]; canCreate: boolean; onCreate: () => void }) {
  return (
    <section className="device-section">
      <div className="device-section-title">
        <div><Wrench size={18} /><span><h2>Repair Tickets</h2><p>Device repair lifecycle from opening through verification and closure.</p></span></div>
        {canCreate && <button onClick={onCreate}><Plus size={15} /> New Ticket</button>}
      </div>
      {tickets.length === 0 ? <p className="device-empty">No repair tickets for this device.</p> : (
        <div className="table-wrap device-table"><table><thead><tr><th>Ticket #</th><th>Title</th><th>Severity</th><th>Technician</th><th>Status</th><th>Created</th><th>Updated</th></tr></thead><tbody>
          {tickets.map((ticket) => <tr key={ticket.id}><td className="mono">{ticket.ticket_number}</td><td><strong>{ticket.title}</strong><span className="table-sub">{ticket.category}</span></td><td><StatusBadge value={ticket.severity} /></td><td>{ticket.assigned_technician?.full_name || "Unassigned"}</td><td><StatusBadge value={ticket.status} /></td><td>{formatDateTime(ticket.created_at)}</td><td>{formatDateTime(ticket.updated_at)}</td></tr>)}
        </tbody></table></div>
      )}
    </section>
  );
}
