import { FormEvent, useEffect, useState } from "react";
import { Headphones, UploadCloud, Wrench, X } from "lucide-react";

export type DeviceDialogMode = "ticket" | "maintenance" | "remote" | "agent" | null;

export function DeviceActionDialog({
  mode,
  deviceName,
  currentAgentVersion,
  latestAgentVersion,
  submitting,
  onClose,
  onCreateTicket,
  onLogMaintenance,
  onOpenAgentManagement,
}: {
  mode: DeviceDialogMode;
  deviceName: string;
  currentAgentVersion: string | null;
  latestAgentVersion: string | null;
  submitting: boolean;
  onClose: () => void;
  onCreateTicket: (payload: { severity: string; category: string; title: string; description: string }) => Promise<void>;
  onLogMaintenance: (payload: { maintenance_type: string; problem_description: string; actions_taken: string; parts_replaced: string; status: string; notes: string }) => Promise<void>;
  onOpenAgentManagement: () => void;
}) {
  const [ticket, setTicket] = useState({ severity: "medium", category: "manual", title: "", description: "" });
  const [maintenance, setMaintenance] = useState({ maintenance_type: "preventive", problem_description: "", actions_taken: "", parts_replaced: "", status: "completed", notes: "" });

  useEffect(() => {
    if (mode === "ticket") setTicket({ severity: "medium", category: "manual", title: "", description: "" });
    if (mode === "maintenance") setMaintenance({ maintenance_type: "preventive", problem_description: "", actions_taken: "", parts_replaced: "", status: "completed", notes: "" });
  }, [mode]);

  if (!mode) return null;

  async function submitTicket(event: FormEvent) {
    event.preventDefault();
    await onCreateTicket(ticket);
  }

  async function submitMaintenance(event: FormEvent) {
    event.preventDefault();
    await onLogMaintenance(maintenance);
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal device-action-modal" role="dialog" aria-modal="true" aria-label={`${mode} action for ${deviceName}`}>
        <header className="modal-header">
          <div className="modal-title">
            <span className="modal-icon">{mode === "remote" ? <Headphones size={20} /> : mode === "agent" ? <UploadCloud size={20} /> : <Wrench size={20} />}</span>
            <div><h2>{mode === "ticket" ? "New Repair Ticket" : mode === "maintenance" ? "Log Maintenance" : mode === "remote" ? "Remote Support" : "Agent Update"}</h2><p>{deviceName}</p></div>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Close dialog"><X size={18} /></button>
        </header>

        {mode === "ticket" && <form className="device-form" onSubmit={submitTicket}>
          <label>Title<input value={ticket.title} onChange={(event) => setTicket({ ...ticket, title: event.target.value })} required maxLength={240} /></label>
          <label>Description<textarea value={ticket.description} onChange={(event) => setTicket({ ...ticket, description: event.target.value })} required maxLength={4000} /></label>
          <div className="form-row">
            <label>Severity<select value={ticket.severity} onChange={(event) => setTicket({ ...ticket, severity: event.target.value })}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></select></label>
            <label>Category<input value={ticket.category} onChange={(event) => setTicket({ ...ticket, category: event.target.value })} /></label>
          </div>
          <footer className="modal-footer"><button type="button" className="secondary" onClick={onClose}>Cancel</button><button type="submit" disabled={submitting}>{submitting ? "Creating..." : "Create Ticket"}</button></footer>
        </form>}

        {mode === "maintenance" && <form className="device-form" onSubmit={submitMaintenance}>
          <div className="form-row">
            <label>Maintenance Type<select value={maintenance.maintenance_type} onChange={(event) => setMaintenance({ ...maintenance, maintenance_type: event.target.value })}><option value="preventive">Preventive</option><option value="corrective">Corrective</option><option value="inspection">Inspection</option><option value="cleaning">Cleaning</option><option value="software">Software</option><option value="hardware">Hardware</option></select></label>
            <label>Status<select value={maintenance.status} onChange={(event) => setMaintenance({ ...maintenance, status: event.target.value })}><option value="scheduled">Scheduled</option><option value="in_progress">In progress</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option></select></label>
          </div>
          <label>Problem Description<textarea value={maintenance.problem_description} onChange={(event) => setMaintenance({ ...maintenance, problem_description: event.target.value })} /></label>
          <label>Actions Taken<textarea value={maintenance.actions_taken} onChange={(event) => setMaintenance({ ...maintenance, actions_taken: event.target.value })} /></label>
          <label>Parts Replaced<input value={maintenance.parts_replaced} onChange={(event) => setMaintenance({ ...maintenance, parts_replaced: event.target.value })} /></label>
          <label>Notes<textarea value={maintenance.notes} onChange={(event) => setMaintenance({ ...maintenance, notes: event.target.value })} /></label>
          <footer className="modal-footer"><button type="button" className="secondary" onClick={onClose}>Cancel</button><button type="submit" disabled={submitting}>{submitting ? "Saving..." : "Save Maintenance Log"}</button></footer>
        </form>}

        {mode === "remote" && <div className="integration-message"><Headphones size={28} /><h3>Remote support integration not configured.</h3><p>No connection has been opened. Remote support requires an authorized user, an authorized device, and an explicit configured support provider.</p><button onClick={onClose}>Close</button></div>}

        {mode === "agent" && <div className="integration-message"><UploadCloud size={28} /><h3>{currentAgentVersion === latestAgentVersion ? "Agent is up to date" : "Controlled update required"}</h3><p>Installed: {currentAgentVersion || "Not reported"} • Latest: {latestAgentVersion || "Not reported"}</p><p>PC Sentinel does not execute arbitrary remote PowerShell. Use the authenticated Agent Management installer workflow to update this device.</p><div className="header-actions"><button className="secondary" onClick={onClose}>Cancel</button><button onClick={onOpenAgentManagement}>Open Agent Management</button></div></div>}
      </section>
    </div>
  );
}
