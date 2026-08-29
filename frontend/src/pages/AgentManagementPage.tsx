import { Bot, Clipboard, KeyRound, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { LoadingBlock } from "../components/LoadingBlock";
import { StatusBadge } from "../components/StatusBadge";
import { API_BASE_URL, apiFetch } from "../lib/api";
import { Computer } from "../types/models";

export function AgentManagementPage() {
  const [agents, setAgents] = useState<Computer[]>([]);
  const [registrationCode, setRegistrationCode] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const installCommand = useMemo(() => {
    if (!registrationCode) return "";
    return `powershell -NoProfile -ExecutionPolicy Bypass -File .\\pc-monitoring-agent.ps1 -ApiBaseUrl "${API_BASE_URL}" -RegistrationCode "${registrationCode}" -InstallAsStartupTask`;
  }, [registrationCode]);

  async function load() {
    setError("");
    setLoading(true);
    try {
      const data = await apiFetch<{ items: Computer[] }>("/agents");
      setAgents(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load agents");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function generateCode() {
    setError("");
    setNotice("");
    try {
      const data = await apiFetch<{ code: string }>("/agents/registration-codes", { method: "POST" });
      setRegistrationCode(data.code);
      setNotice("Registration code generated. It expires after 24 hours.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate registration code");
    }
  }

  async function copyCommand() {
    if (!installCommand) return;
    await navigator.clipboard.writeText(installCommand);
    setNotice("Installation command copied.");
  }

  return (
    <div className="page">
      <header className="page-header row">
        <div>
          <h1>Agent Management</h1>
          <p>Generate registration codes, track agent heartbeat state, and verify agent versions.</p>
        </div>
        <div className="header-actions">
          <button className="secondary" onClick={load}><RefreshCw size={16} /> Refresh</button>
          <button onClick={generateCode}><KeyRound size={16} /> Generate Code</button>
        </div>
      </header>
      {error && <p className="error">{error}</p>}
      {notice && <p className="success">{notice}</p>}
      {registrationCode && (
        <section className="panel">
          <h2><Bot size={18} /> PowerShell Installation</h2>
          <div className="code-row">
            <pre>{installCommand}</pre>
            <button onClick={copyCommand} aria-label="Copy installation command"><Clipboard size={16} /></button>
          </div>
        </section>
      )}
      {loading ? <LoadingBlock /> : agents.length === 0 ? <p className="empty">No agents have registered yet.</p> : (
        <div className="table-wrap sentinel-table">
          <table>
            <thead>
              <tr>
                <th>Device</th><th>Agent</th><th>Version</th><th>Capabilities</th><th>Last heartbeat</th><th>Status</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((agent) => (
                <tr key={agent.id}>
                  <td>
                    <strong>{agent.display_name ?? agent.computer_name}</strong>
                    <span className="table-sub">{agent.device_id}</span>
                  </td>
                  <td>{agent.agent_status ?? "unknown"}</td>
                  <td>{agent.agent_version ?? "-"}</td>
                  <td>{agent.capabilities?.join(", ") || "-"}</td>
                  <td>{agent.last_heartbeat ? new Date(agent.last_heartbeat).toLocaleString() : "never"}</td>
                  <td><StatusBadge value={agent.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
