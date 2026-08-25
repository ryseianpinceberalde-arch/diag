import { Activity, Cpu, HardDrive, MemoryStick, Network, Thermometer, Wind } from "lucide-react";
import { useEffect, useState } from "react";
import { FanSpeedBadge } from "../components/FanSpeedBadge";
import { LoadingBlock } from "../components/LoadingBlock";
import { StatusBadge } from "../components/StatusBadge";
import { TemperatureBadge } from "../components/TemperatureBadge";
import { UsageProgressBar } from "../components/UsageProgressBar";
import { apiFetch } from "../lib/api";
import { Computer } from "../types/models";

export function LiveMonitoringPage() {
  const [computers, setComputers] = useState<Computer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch<{ items: Computer[] }>("/computers")
      .then((data) => setComputers(data.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page">
      <header className="page-header">
        <h1>Live Telemetry Grid</h1>
        <p>Current readings from registered monitoring agents.</p>
      </header>
      {error && <p className="error">{error}</p>}
      {loading ? <LoadingBlock /> : computers.length === 0 ? <p className="empty">No live agents are reporting yet.</p> : (
        <div className="telemetry-grid">
          {computers.map((computer) => {
            const reading = computer.latest_reading;
            const hasFan = reading?.fan_speed_rpm != null || reading?.fan_speed_percent != null;
            const hasNetwork = reading?.network_latency != null || reading?.packet_loss != null;

            return (
              <section className="telemetry-card" key={computer.id}>
                <div className="telemetry-head">
                  <div>
                    <strong>{computer.computer_name}</strong>
                    <span>{computer.ip_address ?? "No IP"} - {computer.operating_system ?? "Unknown OS"}</span>
                  </div>
                  <StatusBadge value={computer.status} />
                </div>
                <div className="telemetry-icons">
                  <span><Cpu size={16} /> CPU</span>
                  <span><MemoryStick size={16} /> RAM</span>
                  <span><HardDrive size={16} /> Disk</span>
                  <span><Thermometer size={16} /> Temp</span>
                  {hasFan && <span><Wind size={16} /> Fan</span>}
                  {hasNetwork && <span><Network size={16} /> Network</span>}
                </div>
                <UsageProgressBar label="CPU" value={reading?.cpu_usage} />
                <UsageProgressBar label="RAM" value={reading?.ram_usage} />
                <UsageProgressBar label="Disk" value={reading?.disk_usage} />
                <div className="temperature-row">
                  <TemperatureBadge label="CPU temp" value={reading?.cpu_temperature} />
                  <TemperatureBadge label="Disk temp" value={reading?.disk_temperature} />
                </div>
                {hasFan && <FanSpeedBadge label="Fan speed" rpm={reading?.fan_speed_rpm} percent={reading?.fan_speed_percent} />}
                {hasNetwork && (
                  <div className="network-metrics">
                    {reading?.network_latency != null && (
                      <div className="network-metric">
                        <Network size={15} />
                        <span>Latency</span>
                        <strong>{Math.round(reading.network_latency)} ms</strong>
                      </div>
                    )}
                    {reading?.packet_loss != null && <UsageProgressBar label="Packet loss" value={reading.packet_loss} />}
                  </div>
                )}
                <div className="telemetry-foot">
                  <Activity size={15} />
                  Last seen {computer.last_seen ? new Date(computer.last_seen).toLocaleString() : "never"}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
