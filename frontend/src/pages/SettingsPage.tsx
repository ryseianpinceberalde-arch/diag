import { Database, Server, Shield, SlidersHorizontal } from "lucide-react";

export function SettingsPage() {
  return (
    <div className="page">
      <header className="page-header">
        <h1>System Settings</h1>
        <p>Alert thresholds, agent intervals, FastAPI backend and Supabase credentials.</p>
      </header>
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
          <h2>Agent Secret Boundary</h2>
          <p>Agent API keys and service-role keys belong only in backend and agent environments.</p>
        </section>
        <section className="panel setting-card">
          <SlidersHorizontal size={22} />
          <h2>Risk Engine</h2>
          <p>Explainable scoring is active. Scikit-learn support is reserved for future labeled data.</p>
        </section>
      </div>
    </div>
  );
}
