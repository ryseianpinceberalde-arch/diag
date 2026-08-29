import { FormEvent, useEffect, useState } from "react";
import { Save } from "lucide-react";
import { Computer } from "../../types/models";

export function AssetMetadataEditor({ computer, canEdit, saving, onSave }: { computer: Computer; canEdit: boolean; saving: boolean; onSave: (payload: Record<string, unknown>) => Promise<void> }) {
  const [form, setForm] = useState({ display_name: "", asset_tag: "", device_type: "computer", owner_name: "", tags: "", notes: "" });
  useEffect(() => {
    setForm({
      display_name: computer.display_name || computer.computer_name,
      asset_tag: computer.asset_tag || "",
      device_type: computer.device_type || "computer",
      owner_name: computer.owner_name || "",
      tags: (computer.tags || []).join(", "),
      notes: computer.notes || "",
    });
  }, [computer]);

  if (!canEdit) return null;

  async function submit(event: FormEvent) {
    event.preventDefault();
    await onSave({
      ...form,
      tags: form.tags.split(",").map((item) => item.trim()).filter(Boolean),
    });
  }

  return (
    <section className="device-section">
      <div className="device-section-title"><div><Save size={18} /><span><h2>Asset Metadata & Notes</h2><p>Existing inventory metadata retained from the previous device-details page.</p></span></div></div>
      <form className="device-form" onSubmit={submit}>
        <div className="form-row">
          <label>Display Name<input value={form.display_name} onChange={(event) => setForm({ ...form, display_name: event.target.value })} /></label>
          <label>Asset Tag<input value={form.asset_tag} onChange={(event) => setForm({ ...form, asset_tag: event.target.value })} /></label>
          <label>Device Type<select value={form.device_type} onChange={(event) => setForm({ ...form, device_type: event.target.value })}><option value="computer">Computer</option><option value="desktop">Desktop</option><option value="laptop">Laptop</option></select></label>
          <label>Assigned Owner<input value={form.owner_name} onChange={(event) => setForm({ ...form, owner_name: event.target.value })} /></label>
        </div>
        <label>Tags<input value={form.tags} onChange={(event) => setForm({ ...form, tags: event.target.value })} placeholder="office, laptop, priority" /></label>
        <label>Notes<textarea value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></label>
        <button type="submit" disabled={saving}><Save size={15} /> {saving ? "Saving..." : "Save Metadata"}</button>
      </form>
    </section>
  );
}
