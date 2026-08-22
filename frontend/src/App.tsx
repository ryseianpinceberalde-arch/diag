import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Session } from "@supabase/supabase-js";
import { Layout } from "./components/Layout";
import { supabase } from "./lib/supabase";
import { AlertsPage } from "./pages/AlertsPage";
import { ComputerDetailsPage } from "./pages/ComputerDetailsPage";
import { ComputersPage } from "./pages/ComputersPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { LiveMonitoringPage } from "./pages/LiveMonitoringPage";
import { MaintenancePage } from "./pages/MaintenancePage";
import { PredictionsPage } from "./pages/PredictionsPage";
import { ReportsPage } from "./pages/ReportsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { UsersPage } from "./pages/UsersPage";

function RequireAuth({ session, children }: { session: Session | null; children: JSX.Element }) {
  if (!session) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setReady(true);
    });
    const { data } = supabase.auth.onAuthStateChange((_, nextSession) => setSession(nextSession));
    return () => data.subscription.unsubscribe();
  }, []);

  if (!ready) {
    return <div className="app-loading">Loading diagnostics...</div>;
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage session={session} />} />
      <Route path="/" element={<RequireAuth session={session}><Layout /></RequireAuth>}>
        <Route index element={<DashboardPage />} />
        <Route path="computers" element={<ComputersPage />} />
        <Route path="computers/:computerId" element={<ComputerDetailsPage />} />
        <Route path="live-monitoring" element={<LiveMonitoringPage />} />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="predictions" element={<PredictionsPage />} />
        <Route path="maintenance" element={<MaintenancePage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
