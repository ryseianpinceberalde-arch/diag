import { Clipboard, PlusCircle, X } from "lucide-react";
import { useEffect, useState } from "react";
import { apiFetch } from "../lib/api";

export function AddComputerModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [copied, setCopied] = useState<string | null>(null);
  const [onlineInstallCommand, setOnlineInstallCommand] = useState("");
  const [installError, setInstallError] = useState("");

  useEffect(() => {
    if (!open) return;
    setInstallError("");
    apiFetch<{ command: string; expires_hours: number }>("/installer/command")
      .then((data) => setOnlineInstallCommand(data.command))
      .catch((err) => setInstallError(err instanceof Error ? err.message : "Failed to create install command"));
  }, [open]);

  if (!open) return null;

  async function copy(text: string, label: string) {
    await navigator.clipboard.writeText(text);
    setCopied(label);
    window.setTimeout(() => setCopied(null), 1800);
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <section className="modal" role="dialog" aria-modal="true" aria-labelledby="add-computer-title" onClick={(event) => event.stopPropagation()}>
        <header className="modal-header">
          <div className="modal-title">
            <div className="modal-icon"><PlusCircle size={22} /></div>
            <div>
              <h2 id="add-computer-title">Add Computer</h2>
              <p>You do not type computer details here. Run the agent and the computer adds itself automatically.</p>
            </div>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Close add computer dialog"><X size={18} /></button>
        </header>

        <div className="setup-steps">
          <article>
            <strong>Add this computer</strong>
            <p>Open PowerShell on the Windows PC you want to monitor and run this command.</p>
            <div className="code-row">
              <pre>{installError || onlineInstallCommand || "Creating install command..."}</pre>
              <button onClick={() => copy(onlineInstallCommand, "install command")} disabled={!onlineInstallCommand} aria-label="Copy install command"><Clipboard size={15} /></button>
            </div>
            <p className="helper-text">This works for this computer or another Windows PC. It installs Python if needed, downloads the agent, verifies check-in, and starts monitoring.</p>
          </article>

          <article>
            <strong>Install on another computer</strong>
            <p>Copy the same command above and send it to the other Windows PC. The other computer does not need a dashboard login.</p>
            <p className="helper-text">Use a freshly generated command from this dialog because the installer token expires after 24 hours.</p>
          </article>

          <article>
            <strong>Enable hardware sensor readings</strong>
            <p>Windows often hides CPU, disk, and fan sensors. To show real sensor values, run LibreHardwareMonitor or OpenHardwareMonitor on the monitored computer with WMI enabled, then restart `python .\\agent.py`.</p>
            <p className="helper-text">If the hardware does not expose a sensor to Windows, the dashboard shows No sensor while CPU, RAM, disk, and network readings still work.</p>
          </article>

          <article>
            <strong>What happens next</strong>
            <p>The agent detects the computer name, device ID, Windows version, IP address, CPU, RAM, disk, fan, and network readings. It appears in inventory after the first successful check-in.</p>
          </article>
        </div>

        <footer className="modal-footer">
          <p>{copied ? `Copied ${copied}.` : "Only dashboard admins can see computers. The installed agent cannot open the dashboard."}</p>
          <button onClick={onClose}>Done</button>
        </footer>
      </section>
    </div>
  );
}
