import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { AssetMetadataEditor } from "../components/device/AssetMetadataEditor";
import { DeviceActionDialog, DeviceDialogMode } from "../components/device/DeviceActionDialog";
import { DeviceHeader } from "../components/device/DeviceHeader";
import { DeviceSummaryCards } from "../components/device/DeviceSummaryCards";
import { DiagnosticFindings } from "../components/device/DiagnosticFindings";
import { HardwareSpecifications } from "../components/device/HardwareSpecifications";
import { LiveTelemetryCards } from "../components/device/TelemetryCards";
import { MaintenanceLog } from "../components/device/MaintenanceLog";
import { MonitoringTabs } from "../components/device/MonitoringTabs";
import { ProcessTable } from "../components/device/ProcessTable";
import { RepairTicketList } from "../components/device/RepairTicketList";
import { StorageVolumes } from "../components/device/StorageVolumes";
import { TelemetryHistory } from "../components/device/TelemetryHistory";
import { WifiDiagnostics } from "../components/device/WifiDiagnostics";
import { DEFAULT_PERMISSIONS, DEFAULT_SETTINGS, DeviceDetailResponse, DeviceHardware, DeviceOperationalData, MonitoringTab } from "../components/device/types";
import { LoadingBlock } from "../components/LoadingBlock";
import { StatusBadge } from "../components/StatusBadge";
import { apiDownload, apiFetch } from "../lib/api";
import { asRecord, asRecordArray, asText, formatDateTime } from "../lib/formatters";
import { AppSettings, DiagnosticFinding, DiagnosticReading, MaintenanceRecord, RepairTicket } from "../types/models";

const EMPTY_HARDWARE: DeviceHardware = { system: {}, cpu: {}, memory: {}, storage: [], gpu: [], battery: null };
const EMPTY_OPERATIONAL: DeviceOperationalData = { hardware: EMPTY_HARDWARE, network: [], processes: [], findings: [], tickets: [], maintenance: [] };

export function ComputerDetailsPage() {
  const { computerId } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<DeviceDetailResponse | null>(null);
  const [history, setHistory] = useState<DiagnosticReading[]>([]);
  const [operational, setOperational] = useState<DeviceOperationalData>(EMPTY_OPERATIONAL);
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [latestAgentVersion, setLatestAgentVersion] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<MonitoringTab>("telemetry");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [processRefreshing, setProcessRefreshing] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [savingMetadata, setSavingMetadata] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [creatingTicketId, setCreatingTicketId] = useState<string | null>(null);
  const [dialog, setDialog] = useState<DeviceDialogMode>(null);
  const [error, setError] = useState("");
  const [relatedError, setRelatedError] = useState("");
  const [notice, setNotice] = useState("");

  const applyDetail = useCallback((data: DeviceDetailResponse) => {
    const inventory = data.computer.agent_inventory || {};
    setDetail({ ...data, permissions: data.permissions || DEFAULT_PERMISSIONS });
    setOperational((current) => ({
      ...current,
      hardware: {
        system: asRecord(inventory.system),
        cpu: asRecord(inventory.cpu),
        memory: asRecord(inventory.memory),
        storage: asRecordArray(inventory.storage),
        gpu: asRecordArray(inventory.gpu),
        battery: inventory.battery ? asRecord(inventory.battery) : null,
      },
      network: asRecordArray(inventory.network),
      processes: asRecordArray(inventory.processes),
    }));
    if (data.latest_reading) {
      setHistory((current) => current.some((item) => item.id === data.latest_reading?.id) ? current : [...current, data.latest_reading as DiagnosticReading].slice(-200));
    }
  }, []);

  const loadOperationalRecords = useCallback(async () => {
    if (!computerId) return;
    const results = await Promise.allSettled([
      apiFetch<{ items: DiagnosticFinding[] }>(`/diagnostics?computer_id=${encodeURIComponent(computerId)}`),
      apiFetch<{ items: RepairTicket[] }>(`/tickets?computer_id=${encodeURIComponent(computerId)}`),
      apiFetch<{ items: MaintenanceRecord[] }>(`/maintenance/records?computer_id=${encodeURIComponent(computerId)}`),
    ]);
    setOperational((current) => ({
      ...current,
      findings: results[0].status === "fulfilled" ? results[0].value.items : current.findings,
      tickets: results[1].status === "fulfilled" ? results[1].value.items : current.tickets,
      maintenance: results[2].status === "fulfilled" ? results[2].value.items : current.maintenance,
    }));
    setRelatedError(results.some((result) => result.status === "rejected") ? "Some diagnostic, ticket, or maintenance records could not be loaded. Confirm that the latest Supabase migrations are applied." : "");
  }, [computerId]);

  const loadInitial = useCallback(async () => {
    if (!computerId) return;
    setLoading(true);
    setError("");
    setRelatedError("");
    const recordsPromise = loadOperationalRecords();
    try {
      const [detailData, historyData, settingsData, versionData] = await Promise.all([
        apiFetch<DeviceDetailResponse>(`/devices/${computerId}`),
        apiFetch<{ readings: DiagnosticReading[] }>(`/devices/${computerId}/history?limit=200`),
        apiFetch<{ settings: AppSettings }>("/settings"),
        apiFetch<{ latestVersion: string }>("/agents/version"),
      ]);
      setHistory(historyData.readings);
      setSettings(settingsData.settings);
      setLatestAgentVersion(versionData.latestVersion);
      applyDetail(detailData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to retrieve device monitoring data.");
    } finally {
      await recordsPromise;
      setLoading(false);
    }
  }, [applyDetail, computerId, loadOperationalRecords]);

  const loadDetail = useCallback(async () => {
    if (!computerId) return;
    try {
      const data = await apiFetch<DeviceDetailResponse>(`/devices/${computerId}`);
      applyDetail(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to refresh device monitoring data.");
    }
  }, [applyDetail, computerId]);

  const loadActiveTab = useCallback(async () => {
    if (!computerId) return;
    try {
      if (activeTab === "processes") {
        const data = await apiFetch<{ items: Array<Record<string, unknown>> }>(`/devices/${computerId}/processes`);
        setOperational((current) => ({ ...current, processes: data.items }));
      } else if (activeTab === "wifi") {
        const data = await apiFetch<{ items: Array<Record<string, unknown>> }>(`/devices/${computerId}/network`);
        setOperational((current) => ({ ...current, network: data.items }));
      } else if (["findings", "tickets", "maintenance"].includes(activeTab)) {
        await loadOperationalRecords();
      }
    } catch {
      setRelatedError("Unable to refresh the selected monitoring section.");
    }
  }, [activeTab, computerId, loadOperationalRecords]);

  useEffect(() => { loadInitial(); }, [loadInitial]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      loadDetail();
      loadActiveTab();
    }, 15_000);
    return () => window.clearInterval(timer);
  }, [loadActiveTab, loadDetail]);

  async function refreshAll() {
    setRefreshing(true);
    setError("");
    await Promise.all([loadDetail(), loadActiveTab()]);
    setRefreshing(false);
  }

  async function refreshProcesses() {
    if (!computerId) return;
    setProcessRefreshing(true);
    try {
      const data = await apiFetch<{ items: Array<Record<string, unknown>> }>(`/devices/${computerId}/processes`);
      setOperational((current) => ({ ...current, processes: data.items }));
    } catch (err) {
      setRelatedError(err instanceof Error ? err.message : "Unable to refresh processes.");
    } finally {
      setProcessRefreshing(false);
    }
  }

  async function runAnalysis() {
    if (!computerId) return;
    setAnalyzing(true);
    setError("");
    try {
      await apiFetch(`/devices/${computerId}/analyze`, { method: "POST" });
      await Promise.all([loadDetail(), loadOperationalRecords()]);
      setNotice("Device analysis completed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Device analysis failed.");
    } finally {
      setAnalyzing(false);
    }
  }

  async function downloadReport() {
    if (!computerId || !detail) return;
    try {
      const blob = await apiDownload(`/devices/${computerId}/report`);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `pc-sentinel-${detail.computer.computer_name}.html`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to download the device report.");
    }
  }

  async function deleteDevice() {
    if (!computerId || !detail) return;
    if (!window.confirm(`Delete ${detail.computer.computer_name} and its monitoring history? This action cannot be undone.`)) return;
    try {
      await apiFetch(`/devices/${computerId}`, { method: "DELETE" });
      navigate("/computers");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete this device.");
    }
  }

  async function createTicket(payload: { severity: string; category: string; title: string; description: string }) {
    if (!computerId) return;
    setSubmitting(true);
    try {
      await apiFetch("/tickets", { method: "POST", body: JSON.stringify({ ...payload, computer_id: computerId }) });
      setDialog(null);
      setNotice("Repair ticket created.");
      await loadOperationalRecords();
      setActiveTab("tickets");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create repair ticket.");
    } finally {
      setSubmitting(false);
    }
  }

  async function createTicketFromFinding(findingId: string) {
    setCreatingTicketId(findingId);
    try {
      const response = await apiFetch<{ created: boolean; ticket: { ticket_number: string } }>(`/diagnostics/${findingId}/ticket`, { method: "POST", body: JSON.stringify({}) });
      setNotice(response.created ? `Created ${response.ticket.ticket_number}.` : `${response.ticket.ticket_number} is already open.`);
      await loadOperationalRecords();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create a ticket from this finding.");
    } finally {
      setCreatingTicketId(null);
    }
  }

  async function logMaintenance(payload: { maintenance_type: string; problem_description: string; actions_taken: string; parts_replaced: string; status: string; notes: string }) {
    if (!computerId) return;
    setSubmitting(true);
    try {
      await apiFetch("/maintenance/records", { method: "POST", body: JSON.stringify({ ...payload, computer_id: computerId }) });
      setDialog(null);
      setNotice("Maintenance record saved.");
      await loadOperationalRecords();
      setActiveTab("maintenance");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save maintenance record.");
    } finally {
      setSubmitting(false);
    }
  }

  async function saveMetadata(payload: Record<string, unknown>) {
    if (!computerId) return;
    setSavingMetadata(true);
    try {
      await apiFetch(`/devices/${computerId}`, { method: "PATCH", body: JSON.stringify(payload) });
      await loadDetail();
      setNotice("Asset metadata saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save asset metadata.");
    } finally {
      setSavingMetadata(false);
    }
  }

  const primaryNetwork = useMemo(() => operational.network.find((item) => ["connected", "up"].includes((asText(item.status) || "").toLowerCase())) || operational.network[0] || {}, [operational.network]);
  const networkFinding = operational.findings.find((finding) => finding.component === "network" && ["active", "acknowledged"].includes(finding.status));

  if (loading) return <div className="page"><div className="device-skeleton-grid"><LoadingBlock /><LoadingBlock /><LoadingBlock /></div></div>;
  if (!detail) return <div className="page"><section className="device-error-state"><AlertTriangle size={30} /><h1>Unable to retrieve device monitoring data.</h1><p>{error}</p><button onClick={loadInitial}><RefreshCw size={16} /> Retry</button></section></div>;

  const inventory = detail.computer.agent_inventory || {};
  const temperature = asRecord(inventory.temperature);
  const battery = operational.hardware.battery || {};
  const offline = ["offline", "connection_lost", "waiting_for_agent"].includes(detail.computer.status);
  const counts = { processes: operational.processes.length, findings: operational.findings.length, tickets: operational.tickets.length, maintenance: operational.maintenance.length };

  return (
    <div className="page device-page">
      <DeviceHeader
        computer={detail.computer}
        permissions={detail.permissions}
        latestAgentVersion={latestAgentVersion}
        refreshing={refreshing}
        analyzing={analyzing}
        onBack={() => navigate("/computers")}
        onRefresh={refreshAll}
        onAnalyze={runAnalysis}
        onReport={downloadReport}
        onUpdateAgent={() => setDialog("agent")}
        onRemoteSupport={() => setDialog("remote")}
        onLogMaintenance={() => setDialog("maintenance")}
        onNewTicket={() => setDialog("ticket")}
        onDelete={deleteDevice}
      />
      {error && <p className="error">{error}</p>}
      {relatedError && <p className="warning-message">{relatedError}</p>}
      {notice && <p className="success">{notice}</p>}
      <DeviceSummaryCards computer={detail.computer} reading={detail.latest_reading} assignedUser={detail.assigned_user} system={operational.hardware.system} primaryNetwork={primaryNetwork} />
      {offline && <div className="offline-banner"><AlertTriangle size={18} /><div><strong>Device is offline — Last Reported Telemetry</strong><span>Last telemetry: {formatDateTime(detail.latest_reading?.recorded_at || detail.computer.last_heartbeat || detail.computer.last_seen)}</span></div></div>}
      {detail.latest_prediction && <div className="prediction-strip"><span>Latest prediction</span><StatusBadge value={detail.latest_prediction.risk_level} /><strong>{detail.latest_prediction.risk_score}/100 — {detail.latest_prediction.suspected_component}</strong><p>{detail.latest_prediction.recommended_action}</p></div>}
      <MonitoringTabs active={activeTab} counts={counts} onChange={setActiveTab} />

      {activeTab === "telemetry" && <div className="device-tab-content">
        <div className="device-tab-heading"><div><h2>{offline ? "Last Reported Telemetry" : "Live Telemetry & Sensors"}</h2><p>{offline ? "Readings below are historical and are not presented as live." : "Automatically refreshed every 15 seconds."}</p></div><StatusBadge value={offline ? "offline" : "live"} /></div>
        <LiveTelemetryCards reading={detail.latest_reading} cpu={operational.hardware.cpu} memory={operational.hardware.memory} network={primaryNetwork} temperature={temperature} battery={battery} system={operational.hardware.system} deviceType={detail.computer.device_type} settings={settings} offline={offline} />
        <StorageVolumes storage={operational.hardware.storage} settings={settings} />
        <TelemetryHistory readings={history} />
      </div>}
      {activeTab === "wifi" && <WifiDiagnostics network={operational.network} finding={networkFinding} />}
      {activeTab === "hardware" && <div className="device-tab-content"><HardwareSpecifications computer={detail.computer} hardware={operational.hardware} network={operational.network} /><AssetMetadataEditor computer={detail.computer} canEdit={detail.permissions.edit_device} saving={savingMetadata} onSave={saveMetadata} /></div>}
      {activeTab === "processes" && <ProcessTable processes={operational.processes} refreshing={processRefreshing} onRefresh={refreshProcesses} />}
      {activeTab === "findings" && <DiagnosticFindings findings={operational.findings} canCreateTicket={detail.permissions.create_ticket} creatingTicketId={creatingTicketId} onCreateTicket={createTicketFromFinding} />}
      {activeTab === "tickets" && <RepairTicketList tickets={operational.tickets} canCreate={detail.permissions.create_ticket} onCreate={() => setDialog("ticket")} />}
      {activeTab === "maintenance" && <MaintenanceLog records={operational.maintenance} canCreate={detail.permissions.log_maintenance} onCreate={() => setDialog("maintenance")} />}

      <DeviceActionDialog mode={dialog} deviceName={detail.computer.display_name || detail.computer.computer_name} currentAgentVersion={detail.computer.agent_version} latestAgentVersion={latestAgentVersion} submitting={submitting} onClose={() => setDialog(null)} onCreateTicket={createTicket} onLogMaintenance={logMaintenance} onOpenAgentManagement={() => navigate("/agents")} />
    </div>
  );
}
