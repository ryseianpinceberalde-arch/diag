import { ArrowLeft, Download, Headphones, RefreshCw, ShieldCheck, Trash2, UploadCloud, Wrench } from "lucide-react";
import { Computer } from "../../types/models";
import { StatusBadge } from "../StatusBadge";
import { DevicePermissions } from "./types";

export function DeviceHeader({
  computer,
  permissions,
  latestAgentVersion,
  refreshing,
  analyzing,
  onBack,
  onRefresh,
  onAnalyze,
  onReport,
  onUpdateAgent,
  onRemoteSupport,
  onLogMaintenance,
  onNewTicket,
  onDelete,
}: {
  computer: Computer;
  permissions: DevicePermissions;
  latestAgentVersion: string | null;
  refreshing: boolean;
  analyzing: boolean;
  onBack: () => void;
  onRefresh: () => void;
  onAnalyze: () => void;
  onReport: () => void;
  onUpdateAgent: () => void;
  onRemoteSupport: () => void;
  onLogMaintenance: () => void;
  onNewTicket: () => void;
  onDelete: () => void;
}) {
  const currentVersion = computer.agent_version;
  const agentCurrent = Boolean(currentVersion && latestAgentVersion && currentVersion === latestAgentVersion);
  const agentLabel = agentCurrent ? "Agent Up To Date" : latestAgentVersion ? `Update Agent (${latestAgentVersion})` : "Update Agent";
  const deviceName = computer.display_name || computer.computer_name;

  return (
    <section className="device-hero">
      <div className="device-hero-main">
        <button className="device-back" onClick={onBack} aria-label="Back to computers"><ArrowLeft size={18} /></button>
        <div>
          <div className="device-title-line">
            <h1>{deviceName}</h1>
            <StatusBadge value={computer.status} />
          </div>
          <p>
            Asset ID: <strong>{computer.asset_tag || computer.device_id}</strong>
            <span aria-hidden="true"> • </span>
            Form Factor: <strong>{computer.device_type || "Not reported"}</strong>
          </p>
          <small>Agent {currentVersion || "not reported"}</small>
        </div>
      </div>
      <div className="device-actions">
        <button className="secondary" onClick={onRefresh} disabled={refreshing}><RefreshCw size={15} className={refreshing ? "spin" : ""} /> Refresh</button>
        {permissions.download_report && <button className="secondary" onClick={onReport}><Download size={15} /> Report</button>}
        {permissions.run_analysis && <button className="secondary" onClick={onAnalyze} disabled={analyzing}><ShieldCheck size={15} /> {analyzing ? "Analyzing" : "Run Analysis"}</button>}
        {permissions.update_agent && <button className="secondary" onClick={onUpdateAgent} disabled={agentCurrent}><UploadCloud size={15} /> {agentLabel}</button>}
        {permissions.remote_support && <button className="secondary" onClick={onRemoteSupport}><Headphones size={15} /> Remote Support</button>}
        {permissions.log_maintenance && <button className="secondary" onClick={onLogMaintenance}><Wrench size={15} /> Log Maintenance</button>}
        {permissions.create_ticket && <button onClick={onNewTicket}>+ New Ticket</button>}
        {permissions.delete_device && <button className="danger-button" onClick={onDelete}><Trash2 size={15} /> Delete</button>}
      </div>
    </section>
  );
}
