import { Download, Eye, PlusCircle, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { LoadingBlock } from "../components/LoadingBlock";
import { AddComputerModal } from "../components/AddComputerModal";
import { RiskScoreIndicator } from "../components/RiskScoreIndicator";
import { StatusBadge } from "../components/StatusBadge";
import { TemperatureBadge } from "../components/TemperatureBadge";
import { UsageProgressBar } from "../components/UsageProgressBar";
import { FanSpeedBadge } from "../components/FanSpeedBadge";
import { apiFetch } from "../lib/api";
import { exportCsv } from "../lib/export";
import { Computer } from "../types/models";

export function ComputersPage() {
  const [computers, setComputers] = useState<Computer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [addOpen, setAddOpen] = useState(false);
  const [searchParams] = useSearchParams();
  const search = (searchParams.get("search") ?? "").toLowerCase();

  async function load() {
    setLoading(true);
    setError("");
    try {
      const data = await apiFetch<{ items: Computer[] }>("/computers");
      setComputers(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load computers");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const filteredComputers = computers.filter((computer) => {
    if (!search) return true;
    return [
      computer.computer_name,
      computer.device_id,
      computer.operating_system,
      computer.ip_address,
      computer.manufacturer,
      computer.model
    ].some((value) => (value ?? "").toLowerCase().includes(search));
  });

  function exportInventory() {
    exportCsv("computer-inventory.csv", filteredComputers.map((computer) => ({
      name: computer.computer_name,
      device_id: computer.device_id,
      operating_system: computer.operating_system,
      ip_address: computer.ip_address,
      cpu_usage: computer.latest_reading?.cpu_usage,
      fan_speed_rpm: computer.latest_reading?.fan_speed_rpm,
      fan_speed_percent: computer.latest_reading?.fan_speed_percent,
      ram_usage: computer.latest_reading?.ram_usage,
      disk_usage: computer.latest_reading?.disk_usage,
      risk_score: computer.latest_prediction?.risk_score ?? 0,
      status: computer.status,
      last_seen: computer.last_seen
    })));
  }

  return (
    <div className="page">
      <header className="page-header row">
        <div>
          <h1>Computer inventory</h1>
          <p>Registered computers appear after a monitoring agent checks in.</p>
        </div>
        <div className="header-actions">
          <button className="secondary" onClick={load}><RefreshCw size={16} /> Refresh</button>
          <button className="secondary" onClick={exportInventory} disabled={filteredComputers.length === 0}><Download size={16} /> Export CSV</button>
          <button onClick={() => setAddOpen(true)}><PlusCircle size={16} /> Add Computer</button>
        </div>
      </header>
      {error && <p className="error">{error}</p>}
      {loading ? <LoadingBlock /> : computers.length === 0 ? <p className="empty">No computers have registered yet.</p> : (
        <div className="table-wrap sentinel-table">
          <table>
            <thead>
              <tr>
                <th>Computer Name</th><th>Device ID</th><th>OS</th><th>IP</th><th>CPU</th><th>RAM</th><th>Disk</th><th>Temperature</th><th>Fan</th><th>Risk Score</th><th>Status</th><th></th>
              </tr>
            </thead>
            <tbody>
              {filteredComputers.map((computer) => (
                <tr key={computer.id}>
                  <td>
                    <strong>{computer.computer_name}</strong>
                    <span className="table-sub">{computer.manufacturer ?? "Unknown"} {computer.model ?? ""}</span>
                  </td>
                  <td className="mono">{computer.device_id.slice(0, 12)}</td>
                  <td>{computer.operating_system ?? "Unknown"}</td>
                  <td>{computer.ip_address ?? "-"}</td>
                  <td><UsageProgressBar label="CPU" value={computer.latest_reading?.cpu_usage} /></td>
                  <td><UsageProgressBar label="RAM" value={computer.latest_reading?.ram_usage} /></td>
                  <td><UsageProgressBar label="Disk" value={computer.latest_reading?.disk_usage} /></td>
                  <td>
                    <div className="temperature-row compact">
                      <TemperatureBadge label="CPU" value={computer.latest_reading?.cpu_temperature} />
                    </div>
                  </td>
                  <td><FanSpeedBadge label="Fan" rpm={computer.latest_reading?.fan_speed_rpm} percent={computer.latest_reading?.fan_speed_percent} /></td>
                  <td><RiskScoreIndicator compact score={computer.latest_prediction?.risk_score ?? 0} /></td>
                  <td><StatusBadge value={computer.status} /></td>
                  <td><Link className="icon-link" to={`/computers/${computer.id}`} aria-label={`View ${computer.computer_name}`}><Eye size={18} /></Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <AddComputerModal open={addOpen} onClose={() => setAddOpen(false)} />
    </div>
  );
}
