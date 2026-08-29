import { ClipboardPlus, ScrollText } from "lucide-react";
import { formatDateTime } from "../../lib/formatters";
import { MaintenanceRecord } from "../../types/models";
import { StatusBadge } from "../StatusBadge";

export function MaintenanceLog({ records, canCreate, onCreate }: { records: MaintenanceRecord[]; canCreate: boolean; onCreate: () => void }) {
  return (
    <section className="device-section">
      <div className="device-section-title">
        <div><ScrollText size={18} /><span><h2>Maintenance Log</h2><p>Preventive, corrective, inspection, cleaning, software, and hardware work.</p></span></div>
        {canCreate && <button onClick={onCreate}><ClipboardPlus size={15} /> Log Maintenance</button>}
      </div>
      {records.length === 0 ? <p className="device-empty">No maintenance records available.</p> : (
        <div className="table-wrap device-table"><table><thead><tr><th>Date</th><th>Type</th><th>Problem</th><th>Actions Taken</th><th>Technician</th><th>Parts Replaced</th><th>Status</th><th>Notes</th></tr></thead><tbody>
          {records.map((record) => <tr key={record.id}><td>{formatDateTime(record.completed_at || record.started_at || record.created_at)}</td><td>{record.maintenance_type}</td><td>{record.problem_description || "Not reported"}</td><td>{record.actions_taken || "Not reported"}</td><td>{record.technician?.full_name || "Unassigned"}</td><td>{record.parts_replaced || "None reported"}</td><td><StatusBadge value={record.status} /></td><td>{record.notes || "–"}</td></tr>)}
        </tbody></table></div>
      )}
    </section>
  );
}
