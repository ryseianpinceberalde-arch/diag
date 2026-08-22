import { Activity, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { LoadingBlock } from "../components/LoadingBlock";
import { RiskScoreIndicator } from "../components/RiskScoreIndicator";
import { StatusBadge } from "../components/StatusBadge";
import { TemperatureBadge } from "../components/TemperatureBadge";
import { UsageProgressBar } from "../components/UsageProgressBar";
import { FanSpeedBadge } from "../components/FanSpeedBadge";
import { apiFetch } from "../lib/api";
import { Alert, Computer, DiagnosticReading, Prediction } from "../types/models";

interface DetailResponse {
  computer: Computer;
  latest_reading: DiagnosticReading | null;
  alerts: Alert[];
  latest_prediction: Prediction | null;
}

export function ComputerDetailsPage() {
  const { computerId } = useParams();
  const [detail, setDetail] = useState<DetailResponse | null>(null);
  const [history, setHistory] = useState<{ readings: DiagnosticReading[]; events: any[] }>({ readings: [], events: [] });
  const [error, setError] = useState("");
  const [analyzing, setAnalyzing] = useState(false);

  const load = useCallback(async () => {
    if (!computerId) return;
    const [detailData, historyData] = await Promise.all([
      apiFetch<DetailResponse>(`/computers/${computerId}`),
      apiFetch<{ readings: DiagnosticReading[]; events: any[] }>(`/computers/${computerId}/history`)
    ]);
    setDetail(detailData);
    setHistory(historyData);
  }, [computerId]);

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, [load]);

  async function analyze() {
    if (!computerId) return;
    setAnalyzing(true);
    try {
      await apiFetch(`/computers/${computerId}/analyze`, { method: "POST" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  }

  if (!detail) {
    return <div className="page">{error && <p className="error">{error}</p>}<LoadingBlock /></div>;
  }

  const chartData = history.readings.map((reading) => ({
    time: new Date(reading.recorded_at).toLocaleTimeString(),
    cpu: reading.cpu_usage,
    ram: reading.ram_usage,
    disk: reading.disk_usage,
    temp: reading.cpu_temperature,
    diskTemp: reading.disk_temperature,
    latency: reading.network_latency,
    loss: reading.packet_loss
  }));

  return (
    <div className="page">
      <header className="page-header row">
        <div>
          <h1>{detail.computer.computer_name}</h1>
          <p>{detail.computer.operating_system ?? "Operating system unknown"}</p>
        </div>
        <button onClick={analyze} disabled={analyzing}><RefreshCw size={16} /> {analyzing ? "Analyzing..." : "Analyze"}</button>
      </header>
      {error && <p className="error">{error}</p>}
      <div className="split">
        <section className="panel">
          <h2>Hardware</h2>
          <dl>
            <dt>Manufacturer</dt><dd>{detail.computer.manufacturer ?? "-"}</dd>
            <dt>Model</dt><dd>{detail.computer.model ?? "-"}</dd>
            <dt>Device ID</dt><dd className="mono">{detail.computer.device_id}</dd>
            <dt>IP address</dt><dd>{detail.computer.ip_address ?? "-"}</dd>
            <dt>Status</dt><dd><StatusBadge value={detail.computer.status} /></dd>
            <dt>Last seen</dt><dd>{detail.computer.last_seen ? new Date(detail.computer.last_seen).toLocaleString() : "-"}</dd>
          </dl>
        </section>
        <section className="panel">
          <h2>Prediction</h2>
          {detail.latest_prediction ? (
            <>
              <RiskScoreIndicator score={detail.latest_prediction.risk_score} />
              <p><StatusBadge value={detail.latest_prediction.risk_level} /> {detail.latest_prediction.suspected_component}</p>
              <p>{detail.latest_prediction.recommended_action}</p>
              <ul>{detail.latest_prediction.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
            </>
          ) : <p className="empty">No prediction has been generated.</p>}
        </section>
      </div>
      <section className="panel">
        <h2>Latest measurements</h2>
        <div className="measurement-grid">
          <UsageProgressBar label="CPU" value={detail.latest_reading?.cpu_usage} />
          <UsageProgressBar label="RAM" value={detail.latest_reading?.ram_usage} />
          <UsageProgressBar label="Disk" value={detail.latest_reading?.disk_usage} />
          <UsageProgressBar label="Packet loss" value={detail.latest_reading?.packet_loss} />
          <TemperatureBadge label="CPU temperature" value={detail.latest_reading?.cpu_temperature} />
          <TemperatureBadge label="Disk temperature" value={detail.latest_reading?.disk_temperature} />
          <FanSpeedBadge label="Fan speed" rpm={detail.latest_reading?.fan_speed_rpm} percent={detail.latest_reading?.fan_speed_percent} />
        </div>
      </section>
      <section className="panel">
        <h2><Activity size={18} /> Measurement history</h2>
        <div className="chart">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <XAxis dataKey="time" hide />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="cpu" stroke="#dc2626" dot={false} />
              <Line type="monotone" dataKey="ram" stroke="#ca8a04" dot={false} />
              <Line type="monotone" dataKey="disk" stroke="#2563eb" dot={false} />
              <Line type="monotone" dataKey="temp" name="CPU temp" stroke="#e11d48" dot={false} />
              <Line type="monotone" dataKey="diskTemp" name="Disk temp" stroke="#f97316" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>
      <div className="split">
        <section className="panel">
          <h2>Alerts</h2>
          {detail.alerts.length === 0 ? <p className="empty">No alerts for this computer.</p> : detail.alerts.map((alert) => (
            <article className="list-item" key={alert.id}>
              <StatusBadge value={alert.severity} />
              <strong>{alert.title}</strong>
              <span>{alert.status}</span>
            </article>
          ))}
        </section>
        <section className="panel">
          <h2>System events</h2>
          {history.events.length === 0 ? <p className="empty">No recent critical or error events.</p> : history.events.map((event) => (
            <article className="list-item" key={event.id}>
              <StatusBadge value={event.severity} />
              <strong>{event.source ?? event.event_type}</strong>
              <span>{event.message}</span>
            </article>
          ))}
        </section>
      </div>
    </div>
  );
}
