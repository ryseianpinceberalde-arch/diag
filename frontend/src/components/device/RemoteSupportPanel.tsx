import { FormEvent, useEffect, useState } from "react";
import { apiFetch } from "../../lib/api";

type Config = { enabled: boolean; rustdesk_id: string };
type Mode = "desktop" | "file_transfer";
type Launch = { uri: string; mode: Mode; rustdesk_id: string };

export function RemoteSupportPanel({ computerId }: { computerId: string }) {
  const [saved, setSaved] = useState<Config | null>(null);
  const [form, setForm] = useState<Config>({ enabled: false, rustdesk_id: "" });
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [launch, setLaunch] = useState<Launch | null>(null);
  const path = `/computers/${encodeURIComponent(computerId)}/remote-support`;
  const dirty = saved?.enabled !== form.enabled || saved?.rustdesk_id !== form.rustdesk_id.replace(/ /g, "").trim();

  useEffect(() => {
    let active = true;
    setBusy(true);
    setSaved(null);
    setLaunch(null);
    setError("");
    apiFetch<Config>(path).then((config) => {
      if (active) { setSaved(config); setForm(config); }
    }).catch((reason: Error) => {
      if (active) setError(reason.message);
    }).finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [path]);

  function edit(config: Config) {
    setForm(config);
    setLaunch(null);
    setNotice("");
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError(""); setLaunch(null); setNotice("");
    try {
      const config = await apiFetch<Config>(path, { method: "PUT", body: JSON.stringify(form) });
      setSaved(config); setForm(config); setNotice("Remote support settings saved for this PC.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to save remote support settings.");
    } finally { setBusy(false); }
  }

  async function prepare(mode: Mode) {
    setBusy(true); setError(""); setLaunch(null); setNotice("");
    try {
      const result = await apiFetch<Launch>(`${path}/launch`, { method: "POST", body: JSON.stringify({ mode }) });
      const command = mode === "desktop" ? "connect" : "file-transfer";
      if (!/^[0-9]{6,16}$/.test(result.rustdesk_id) || result.uri !== `rustdesk://${command}/${result.rustdesk_id}`) {
        throw new Error("The server returned an invalid RustDesk link.");
      }
      setLaunch(result);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to prepare remote support.");
    } finally { setBusy(false); }
  }

  return <div className="device-form">
    <p>Install <a href="https://rustdesk.com/docs/en/client/" target="_blank" rel="noreferrer">RustDesk</a> on your PC and the remote PC. Enter the ID shown on the remote PC below.</p>
    {error && <p role="alert">{error}</p>}
    {busy && <p role="status">Please wait...</p>}
    {saved && <>
      <form className="device-form" onSubmit={save}>
        <label>RustDesk ID<input inputMode="numeric" value={form.rustdesk_id} disabled={busy} maxLength={24} pattern="[0-9 ]{6,24}" required={form.enabled} onChange={(event) => edit({ ...form, rustdesk_id: event.target.value })} placeholder="123 456 789" /></label>
        <label>Remote support<select value={form.enabled ? "enabled" : "disabled"} disabled={busy} onChange={(event) => edit({ ...form, enabled: event.target.value === "enabled" })}><option value="disabled">Disabled</option><option value="enabled">Enabled</option></select></label>
        <button type="submit" disabled={busy}>Save settings</button>
      </form>
      {notice && <p role="status">{notice}</p>}
      {dirty && <p>Save your changes before opening RustDesk.</p>}
      <div className="header-actions">
        <button disabled={busy || dirty || !saved.enabled} onClick={() => prepare("desktop")}>Desktop control</button>
        <button className="secondary" disabled={busy || dirty || !saved.enabled} onClick={() => prepare("file_transfer")}>File transfer</button>
      </div>
      {launch && <div role="status">
        <p>Ready for RustDesk ID {launch.rustdesk_id}.</p>
        <a href={launch.uri}>Open RustDesk {launch.mode === "desktop" ? "desktop" : "file transfer"}</a>
        <p>Allow your browser to open RustDesk. If nothing opens, start RustDesk and enter this ID manually.</p>
      </div>}
    </>}
    <p>Approve the connection in RustDesk on the remote PC and allow keyboard/mouse or file transfer as needed. Use desktop control to edit files, or file transfer to download and upload them.</p>
    <p>Opening RustDesk does not confirm a connection. Disabling this dashboard shortcut does not end an existing RustDesk session; disconnect it in RustDesk.</p>
  </div>;
}
