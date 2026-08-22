import { ShieldCheck, UserCog } from "lucide-react";

export function UsersPage() {
  return (
    <div className="page">
      <header className="page-header">
        <h1>Users & Access</h1>
        <p>Administrator authentication is managed by Supabase Auth and profile roles.</p>
      </header>
      <div className="settings-grid">
        <section className="panel">
          <h2><UserCog size={18} /> Administrator Access</h2>
          <p className="empty">Create users in Supabase Authentication, then add matching rows in the `profiles` table with role `administrator`.</p>
        </section>
        <section className="panel">
          <h2><ShieldCheck size={18} /> Security Boundary</h2>
          <p className="empty">Monitoring agents authenticate only to FastAPI with `X-Agent-Api-Key`; they never connect directly to Supabase.</p>
        </section>
      </div>
    </div>
  );
}
