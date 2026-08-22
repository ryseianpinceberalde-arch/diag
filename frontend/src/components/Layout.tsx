import { Activity, Bell, FileText, Monitor, Settings, Shield, TrendingUp, Wrench } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Header } from "./Header";
import { supabase } from "../lib/supabase";

const links = [
  { to: "/", label: "Dashboard", icon: Activity },
  { to: "/computers", label: "Computers", icon: Monitor },
  { to: "/live-monitoring", label: "Live Monitoring", icon: Activity },
  { to: "/alerts", label: "Alerts", icon: Bell },
  { to: "/predictions", label: "Predictions", icon: TrendingUp },
  { to: "/maintenance", label: "Maintenance", icon: Wrench },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/users", label: "Users & Access", icon: Settings },
  { to: "/settings", label: "Settings", icon: Settings }
];

export function Layout() {
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  async function signOut() {
    await supabase.auth.signOut();
    navigate("/login");
  }

  return (
    <div className="shell">
      {mobileOpen && <button className="sidebar-backdrop" onClick={() => setMobileOpen(false)} aria-label="Close navigation" />}
      <aside className={`sidebar ${mobileOpen ? "open" : ""}`}>
        <div className="brand">
          <div className="brand-mark"><Shield size={22} /></div>
          <div>
            <span>PC SENTINEL</span>
            <small>Predictive Diagnostic</small>
          </div>
        </div>
        <div className="mesh-status">
          <span className="live-dot" />
          <strong>Agent Mesh Active</strong>
        </div>
        <nav>
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink key={`${to}-${label}`} to={to} onClick={() => setMobileOpen(false)} className={({ isActive }) => (isActive ? "active" : "")}>
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
        <button className="ghost" onClick={signOut}>Sign out</button>
      </aside>
      <div className="main-area">
        <Header onSignOut={signOut} onOpenMenu={() => setMobileOpen(true)} />
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
