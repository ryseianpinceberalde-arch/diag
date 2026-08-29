import { Bell, Menu, Search, ShieldAlert, User } from "lucide-react";
import { KeyboardEvent, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { apiFetch } from "../lib/api";

const titles: Record<string, { title: string; subtitle: string }> = {
  "/": {
    title: "System Overview Dashboard",
    subtitle: "Real-time telemetry, failure risk estimates and fleet health indexes"
  },
  "/computers": {
    title: "Computer Inventory",
    subtitle: "Network workstation directory, hardware specifications and live state"
  },
  "/alerts": {
    title: "System Alert Center",
    subtitle: "Hardware anomalies, thermal breaches and Windows event violations"
  },
  "/live-monitoring": {
    title: "Live Telemetry Grid",
    subtitle: "Real-time CPU, RAM, disk and network stream visualization"
  },
  "/predictions": {
    title: "Failure Risk Predictions",
    subtitle: "Explainable component-risk estimates and prevention actions"
  },
  "/maintenance": {
    title: "Preventive Maintenance",
    subtitle: "Scheduled technician interventions, cleanup tasks and patch queues"
  },
  "/reports": {
    title: "Auditing & System Reports",
    subtitle: "Preventive-maintenance recommendations and risk history"
  },
  "/users": {
    title: "User & Access Management",
    subtitle: "Administrator access state and Supabase authentication boundaries"
  },
  "/settings": {
    title: "System Settings",
    subtitle: "Backend, Supabase and monitoring agent configuration"
  }
};

export function Header({ onSignOut, onOpenMenu }: { onSignOut: () => void; onOpenMenu: () => void }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [systemStatus, setSystemStatus] = useState<"healthy" | "warning" | "critical">("healthy");
  const page = location.pathname.startsWith("/computers/")
    ? { title: "Computer Diagnostic Details", subtitle: "Sensor telemetry, component timeline and analysis" }
    : titles[location.pathname] ?? titles["/"];

  function search(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" && query.trim()) {
      navigate(`/computers?search=${encodeURIComponent(query.trim())}`);
    }
  }

  useEffect(() => {
    let cancelled = false;
    apiFetch<{ system_status: "healthy" | "warning" | "critical" }>("/dashboard/summary")
      .then((summary) => {
        if (!cancelled) setSystemStatus(summary.system_status);
      })
      .catch(() => {
        if (!cancelled) setSystemStatus("critical");
      });
    return () => {
      cancelled = true;
    };
  }, [location.pathname]);

  const statusText = systemStatus === "healthy" ? "All Systems Operational" : systemStatus === "warning" ? "Systems Need Attention" : "Critical Systems Need Attention";

  return (
    <header className="topbar">
      <div className="topbar-title">
        <button className="mobile-menu" onClick={onOpenMenu} aria-label="Open navigation">
          <Menu size={18} />
        </button>
        <div>
          <h1>{page.title}</h1>
          <p>{page.subtitle}</p>
        </div>
      </div>
      <div className="topbar-actions">
        <label className="global-search">
          <Search size={15} />
          <input
            placeholder="Search computer, IP, ID..."
            aria-label="Search computers"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={search}
          />
        </label>
        <div className={`system-pill ${systemStatus}`}>
          <span />
          {statusText}
        </div>
        <button className="icon-button" onClick={() => navigate("/alerts")} title="Open alerts" aria-label="Open alerts">
          <Bell size={18} />
        </button>
        <button className="profile-button" onClick={onSignOut}>
          <span className="avatar"><User size={15} /></span>
          <span>Admin</span>
        </button>
        <ShieldAlert className="topbar-alert" size={18} />
      </div>
    </header>
  );
}
