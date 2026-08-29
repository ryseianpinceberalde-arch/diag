import { KeyRound, Plus, Save, UserCog } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { apiFetch } from "../lib/api";
import { Profile } from "../types/models";

const roles = ["super_admin", "it_admin", "administrator", "technician", "department_user", "viewer"] as const;

export function UsersPage() {
  const [users, setUsers] = useState<Profile[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({ email: "", password: "", full_name: "", role: "viewer" });

  async function load() {
    setError("");
    try {
      const data = await apiFetch<{ items: Profile[] }>("/users");
      setUsers(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      await apiFetch("/users", { method: "POST", body: JSON.stringify(form) });
      setForm({ email: "", password: "", full_name: "", role: "viewer" });
      setMessage("User created.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create user");
    }
  }

  async function update(user: Profile, patch: Partial<Profile>) {
    setError("");
    try {
      await apiFetch(`/users/${user.id}`, { method: "PATCH", body: JSON.stringify(patch) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update user");
    }
  }

  async function resetPassword(user: Profile) {
    setError("");
    try {
      await apiFetch(`/users/${user.id}/password-reset`, { method: "POST" });
      setMessage(`Password reset sent to ${user.email}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send password reset");
    }
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Users & Access</h1>
        <p>Manage Supabase Auth profiles, roles, activation state, and password reset flow.</p>
      </header>
      {error && <p className="error">{error}</p>}
      {message && <p className="success">{message}</p>}
      <section className="panel">
        <h2><Plus size={18} /> Create User</h2>
        <form className="settings-grid" onSubmit={create}>
          <label>Email<input value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required /></label>
          <label>Password<input type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} minLength={6} required /></label>
          <label>Full name<input value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} /></label>
          <label>Role<select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })}>{roles.map((role) => <option key={role}>{role}</option>)}</select></label>
          <button type="submit"><Save size={16} /> Create</button>
        </form>
      </section>
      <section className="panel">
        <h2><UserCog size={18} /> Profiles</h2>
        {users.length === 0 ? <p className="empty">No profiles found.</p> : (
          <div className="stack">
            {users.map((user) => (
              <article className="report-row" key={user.id}>
                <div>
                  <strong>{user.full_name || user.email || user.id}</strong>
                  <p>{user.email || "No email stored"} - {user.is_active ? "Active" : "Inactive"}</p>
                </div>
                <select value={user.role} onChange={(event) => update(user, { role: event.target.value as Profile["role"] })} aria-label="Update role">
                  {roles.map((role) => <option key={role}>{role}</option>)}
                </select>
                <button className="secondary" onClick={() => update(user, { is_active: !user.is_active })}>{user.is_active ? "Deactivate" : "Activate"}</button>
                <button className="secondary" onClick={() => resetPassword(user)}><KeyRound size={15} /> Reset</button>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
