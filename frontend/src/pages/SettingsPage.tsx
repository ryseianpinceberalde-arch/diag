import { Database, Save, Server, Shield, SlidersHorizontal } from "lucide-react";
import { useEffect, useState } from "react";
import { apiFetch } from "../lib/api";
import { AppSettings } from "../types/models";

const labels: Record<keyof AppSettings, string> = {
  offline_after_seconds: "Offline after seconds",
  agent_reporting_interval_seconds: "Agent reporting interval seconds",
  disk_warning_percent: "Disk warning %",
  disk_critical_percent: "Disk critical %",
  ram_warning_percent: "RAM warning %",
  ram_critical_percent: "RAM critical %",
  cpu_temperature_warning_c: "CPU temp warning C",
  cpu_temperature_critical_c: "CPU temp critical C",
  packet_loss_warning_percent: "Packet loss warning %",
  packet_loss_critical_percent: "Packet loss critical %",
  latency_warning_ms: "Latency warning ms",
  latency_critical_ms: "Latency critical ms",
  risk_warning_score: "Operational risk warning score",
  risk_critical_score: "Operational risk critical score",
  alert_recovery_readings: "Recovery readings before auto-resolve",
  data_retention_days: "Data retention days",
  notifications_enabled: "Critical alert notifications",
  notification_recipients: "Notification recipients"
};

export function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");

  async function load() {
    setError("");
    try {
      const data = await apiFetch<{ settings: AppSettings }>("/settings");
      setSettings(data.settings);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load settings");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function save() {
    if (!settings) return;
    setSaving(true);
    setError("");
    setSaved("");
    try {
      const data = await apiFetch<{ settings: AppSettings }>("/settings", {
        method: "PATCH",
        body: JSON.stringify(settings)
      });
      setSettings(data.settings);
      setSaved("Settings saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page">
      <header className="page-header row">
        <div>
          <h1>System Settings</h1>
          <p>Alert thresholds, agent intervals, FastAPI backend and Supabase configuration.</p>
        </div>
        <button onClick={save} disabled={!settings || saving}><Save size={16} /> {saving ? "Saving" : "Save Settings"}</button>
      </header>
      {error && <p className="error">{error}</p>}
      {saved && <p className="success">{saved}</p>}
      <div className="settings-grid">
        <section className="panel setting-card">
          <Server size={22} />
          <h2>Backend API</h2>
          <p>{import.meta.env.VITE_API_URL ?? "http://localhost:8000"}</p>
        </section>
        <section className="panel setting-card">
          <Database size={22} />
          <h2>Supabase</h2>
          <p>{import.meta.env.VITE_SUPABASE_URL ? "Frontend anon client configured" : "Missing frontend Supabase configuration"}</p>
        </section>
        <section className="panel setting-card">
          <Shield size={22} />
          <h2>Secret Boundary</h2>
          <p>Agent and service-role secrets stay in backend and agent environments.</p>
        </section>
      </div>
      <section className="panel">
        <h2><SlidersHorizontal size={18} /> Thresholds</h2>
        {!settings ? <p className="empty">Loading settings...</p> : (
          <div className="settings-grid">
            {(Object.keys(labels) as Array<keyof AppSettings>).map((key) => (
              <label key={key}>
                {labels[key]}
                {typeof settings[key] === "boolean" ? (
                  <input
                    type="checkbox"
                    checked={settings[key] as boolean}
                    onChange={(event) => setSettings({ ...settings, [key]: event.target.checked })}
                  />
                ) : Array.isArray(settings[key]) ? (
                  <textarea
                    value={(settings[key] as string[]).join(", ")}
                    onChange={(event) => setSettings({ ...settings, [key]: event.target.value.split(",").map((item) => item.trim()).filter(Boolean) })}
                  />
                ) : (
                  <input
                    type="number"
                    value={settings[key] as number}
                    min={0}
                    onChange={(event) => setSettings({ ...settings, [key]: Number(event.target.value) })}
                  />
                )}
              </label>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
