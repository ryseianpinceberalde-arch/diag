import { Activity, AlertOctagon, AlertTriangle, BellRing, CheckCircle, FileDown, Monitor, PlusCircle, RefreshCw, Sparkles, Thermometer, TrendingUp, Wifi, WifiOff, Wind, Wrench } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { MetricCard } from "../components/MetricCard";
import { LoadingBlock } from "../components/LoadingBlock";
import { AddComputerModal } from "../components/AddComputerModal";
import { apiFetch } from "../lib/api";

interface Summary {
  total_computers: number;
  online_computers: number;
  offline_computers: number;
  healthy_computers: number;
  warning_computers: number;
  critical_computers: number;
  active_alerts: number;
  average_risk_score: number;
  system_status: "healthy" | "warning" | "critical";
  average_cpu_temperature: number | null;
  max_cpu_temperature: number | null;
  average_disk_temperature: number | null;
  max_disk_temperature: number | null;
  average_fan_speed_rpm: number | null;
  average_fan_speed_percent: number | null;
  open_tickets: number;
  trends: Array<{ time: string; cpu: number | null; ram: number | null; disk: number | null }>;
}

export function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState("");
  const [addOpen, setAddOpen] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const navigate = useNavigate();

  async function load() {
    setError("");
    setRefreshing(true);
    try {
      const data = await apiFetch<Summary>("/dashboard/summary");
      setSummary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard summary");
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const timer = window.setInterval(load, 30000);
    return () => window.clearInterval(timer);
  }, [autoRefresh]);

  return (
    <div className="page">
      <header className="page-header row">
        <div>
          <h1>Infrastructure Telemetry & Diagnostic Matrix</h1>
          <p>Current fleet health and preventive-maintenance risk.</p>
        </div>
        <div className="header-actions">
          <label className="toggle">
            <input type="checkbox" checked={autoRefresh} onChange={(event) => setAutoRefresh(event.target.checked)} />
            Auto refresh
          </label>
          <button className="secondary" onClick={load} disabled={refreshing}><RefreshCw size={16} /> {refreshing ? "Refreshing" : "Refresh"}</button>
        </div>
      </header>
      {error && <p className="error">{error}</p>}
      {!summary ? <LoadingBlock /> : (
        <>
          <section className="sentinel-banner">
            <div>
              <span><Sparkles size={17} /> PC Sentinel AI Sentinel Core</span>
              <h2>Infrastructure Telemetry & Diagnostic Matrix</h2>
              <p>Proactive hardware failure estimation, thermal anomaly detection, and continuous health auditing across {summary.total_computers} nodes.</p>
            </div>
            <div className="banner-actions">
              <button onClick={() => setAddOpen(true)}><PlusCircle size={16} /> Add Computer</button>
              <button onClick={() => navigate("/live-monitoring")}><Activity size={16} /> Live Telemetry</button>
              <button onClick={() => navigate("/reports")}><FileDown size={16} /> Generate Report</button>
              <button className="danger" onClick={() => navigate("/alerts")}><BellRing size={16} /> {summary.active_alerts} Alerts</button>
            </div>
          </section>

          <div>
            <h3 className="section-label">System Key Telemetry Metrics</h3>
            <div className="metric-grid">
              <MetricCard label="Total Computers" value={summary.total_computers} icon={Monitor} onClick={() => navigate("/computers")} />
              <MetricCard label="Online Nodes" value={summary.online_computers} icon={Wifi} onClick={() => navigate("/live-monitoring")} />
              <MetricCard label="Offline Nodes" value={summary.offline_computers} icon={WifiOff} onClick={() => navigate("/computers")} />
              <MetricCard label="Healthy Nodes" value={summary.healthy_computers} icon={CheckCircle} onClick={() => navigate("/computers")} />
              <MetricCard label="Warning Nodes" value={summary.warning_computers} icon={AlertTriangle} onClick={() => navigate("/predictions")} />
              <MetricCard label="Critical Nodes" value={summary.critical_computers} icon={AlertOctagon} onClick={() => navigate("/predictions")} />
              <MetricCard label="Active Alerts" value={summary.active_alerts} icon={BellRing} onClick={() => navigate("/alerts")} />
              <MetricCard label="Open Tickets" value={summary.open_tickets} icon={Wrench} onClick={() => navigate("/tickets")} />
              {(summary.average_fan_speed_rpm != null || summary.average_fan_speed_percent != null) && (
                <MetricCard
                  label="Avg Fan Speed"
                  value={summary.average_fan_speed_rpm != null ? `${summary.average_fan_speed_rpm} RPM` : `${summary.average_fan_speed_percent}%`}
                  icon={Wind}
                  onClick={() => navigate("/live-monitoring")}
                />
              )}
              <MetricCard label="Avg Operational Risk" value={`${summary.average_risk_score}%`} icon={TrendingUp} onClick={() => navigate("/predictions")} />
              {summary.average_cpu_temperature != null && <MetricCard label="Avg CPU Temp" value={`${summary.average_cpu_temperature} C`} icon={Thermometer} onClick={() => navigate("/live-monitoring")} />}
              {summary.max_cpu_temperature != null && <MetricCard label="Max CPU Temp" value={`${summary.max_cpu_temperature} C`} icon={Thermometer} onClick={() => navigate("/live-monitoring")} />}
            </div>
          </div>

          <div className="dashboard-grid">
            <section className="panel">
              <div className="panel-title">
                <div>
                  <h2>Overall Computer Health</h2>
                  <p>Live operational state distribution</p>
                </div>
              </div>
              <div className="donut-wrap">
                <ResponsiveContainer width="100%" height={230}>
                  <PieChart>
                    <Pie
                      data={[
                        { name: "Healthy", value: summary.healthy_computers, color: "#10b981" },
                        { name: "Warning", value: summary.warning_computers, color: "#f59e0b" },
                        { name: "Critical", value: summary.critical_computers, color: "#e11d48" },
                        { name: "Offline", value: summary.offline_computers, color: "#94a3b8" }
                      ]}
                      innerRadius={62}
                      outerRadius={86}
                      paddingAngle={4}
                      dataKey="value"
                    >
                      {[ "#10b981", "#f59e0b", "#e11d48", "#94a3b8" ].map((color) => <Cell key={color} fill={color} />)}
                    </Pie>
                    <Tooltip contentStyle={{ background: "#0f172a", borderColor: "#334155", color: "#fff" }} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="donut-center">
                  <strong>{summary.total_computers}</strong>
                  <span>Total Nodes</span>
                </div>
              </div>
            </section>

            <section className="panel wide">
              <div className="panel-title">
                <div>
                  <h2>Network Resource Utilization Trends</h2>
                  <p>Fleet telemetry preview for CPU, RAM and storage usage</p>
                </div>
                <span className="live-chip">Live Stream</span>
              </div>
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={summary.trends.map((point) => ({ ...point, time: new Date(point.time).toLocaleTimeString() }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.18} />
                  <XAxis dataKey="time" tick={{ fontSize: 11, fill: "#94a3b8" }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#94a3b8" }} />
                  <Tooltip contentStyle={{ background: "#0f172a", borderColor: "#334155", color: "#fff" }} />
                  <Area type="monotone" dataKey="cpu" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.16} />
                  <Area type="monotone" dataKey="ram" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.12} />
                  <Area type="monotone" dataKey="disk" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.06} />
                </AreaChart>
              </ResponsiveContainer>
            </section>
          </div>

          <section className="panel">
            <div className="panel-title">
              <div>
              <h2>Operational Risk Distribution</h2>
                <p>Explainable scoring breakdown across enrolled machines</p>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={[
                { tier: "Low", count: Math.max(summary.healthy_computers, 0), fill: "#10b981" },
                { tier: "Medium", count: Math.max(summary.warning_computers, 0), fill: "#f59e0b" },
                { tier: "High", count: Math.max(summary.critical_computers, 0), fill: "#ea580c" },
                { tier: "Critical", count: summary.active_alerts, fill: "#e11d48" }
              ]}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.16} />
                <XAxis dataKey="tier" tick={{ fontSize: 11, fill: "#94a3b8" }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#94a3b8" }} />
                <Tooltip contentStyle={{ background: "#0f172a", borderColor: "#334155", color: "#fff" }} />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {[ "#10b981", "#f59e0b", "#ea580c", "#e11d48" ].map((color) => <Cell key={color} fill={color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </section>
        </>
      )}
      <AddComputerModal open={addOpen} onClose={() => setAddOpen(false)} />
    </div>
  );
}
