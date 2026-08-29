import { Database, HardDrive } from "lucide-react";
import { asNumber, asText, formatBytes, formatPercent, UnknownRecord } from "../../lib/formatters";
import { AppSettings } from "../../types/models";
import { StatusBadge } from "../StatusBadge";
import { TelemetryProgressBar } from "./TelemetryProgressBar";

function storageStatus(usage: number | null, settings: AppSettings): string {
  if (usage === null) return "unavailable";
  if (usage >= settings.disk_critical_percent) return "critical";
  if (usage >= Math.max(90, settings.disk_critical_percent - 5)) return "high";
  if (usage >= Math.min(80, settings.disk_warning_percent)) return "warning";
  return "healthy";
}

export function StorageVolumeCard({ volume, settings }: { volume: UnknownRecord; settings: AppSettings }) {
  const usage = asNumber(volume.usage_percent);
  const free = asNumber(volume.free_bytes);
  const total = asNumber(volume.total_bytes);
  const status = storageStatus(usage, settings);
  return (
    <article className="storage-card">
      <header>
        <span className="storage-icon"><HardDrive size={18} /></span>
        <div>
          <h3>{asText(volume.drive_letter) || "Drive"}</h3>
          <p>{asText(volume.volume_label) || asText(volume.partition_label) || "Logical volume"}</p>
        </div>
        <StatusBadge value={status} />
      </header>
      <div className="storage-meta">
        <span>{asText(volume.drive_type) || "Type not reported"}</span>
        <span>{asText(volume.filesystem) || "Filesystem not reported"}</span>
      </div>
      <TelemetryProgressBar value={usage} warning={settings.disk_warning_percent} critical={settings.disk_critical_percent} label="Storage used" />
      <strong className="storage-capacity">{formatPercent(usage)} used</strong>
      <p>{formatBytes(free)} free / {formatBytes(total)} total</p>
      <dl>
        <dt>Disk model</dt><dd>{asText(volume.disk_model) || "Not reported"}</dd>
        <dt>SMART health</dt><dd>{asText(volume.smart_status) || asText(volume.health) || "Not reported"}</dd>
      </dl>
    </article>
  );
}

export function StorageVolumes({ storage, settings }: { storage: UnknownRecord[]; settings: AppSettings }) {
  return (
    <section className="device-section">
      <div className="device-section-title">
        <div><Database size={18} /><span><h2>Logical Storage Volumes & Free Space</h2><p>Partition utilization and reported disk health.</p></span></div>
      </div>
      {storage.length === 0 ? <p className="device-empty">No storage volumes have been reported by the agent.</p> : (
        <div className="storage-grid">{storage.map((volume, index) => <StorageVolumeCard key={`${asText(volume.drive_letter) || "drive"}-${index}`} volume={volume} settings={settings} />)}</div>
      )}
    </section>
  );
}
