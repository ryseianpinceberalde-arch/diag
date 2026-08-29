export type UnknownRecord = Record<string, unknown>;

export function asRecord(value: unknown): UnknownRecord {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value as UnknownRecord : {};
}

export function asRecordArray(value: unknown): UnknownRecord[] {
  return Array.isArray(value) ? value.map(asRecord) : [];
}

export function asNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const numeric = typeof value === "number" ? value : Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

export function asText(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  const text = String(value).trim();
  return text ? text : null;
}

export function formatData(value: unknown, unavailable = "Not available"): string {
  return asText(value) ?? unavailable;
}

export function formatPercent(value: unknown, unavailable = "Not reported"): string {
  const numeric = asNumber(value);
  return numeric === null ? unavailable : `${numeric.toLocaleString(undefined, { maximumFractionDigits: 1 })}%`;
}

export function formatBytes(value: unknown, unavailable = "Not reported"): string {
  const numeric = asNumber(value);
  if (numeric === null) return unavailable;
  if (numeric === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB", "PB"];
  const index = Math.min(Math.floor(Math.log(Math.abs(numeric)) / Math.log(1024)), units.length - 1);
  return `${(numeric / 1024 ** index).toLocaleString(undefined, { maximumFractionDigits: index > 2 ? 2 : 1 })} ${units[index]}`;
}

export function formatMbps(value: unknown): string {
  const numeric = asNumber(value);
  return numeric === null ? "Not reported" : `${numeric.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 3 })} Mbps`;
}

export function formatTemperature(value: unknown): string {
  const numeric = asNumber(value);
  return numeric === null ? "Sensor unavailable" : `${numeric.toLocaleString(undefined, { maximumFractionDigits: 1 })}°C`;
}

export function formatDuration(seconds: unknown): string {
  const numeric = asNumber(seconds);
  if (numeric === null) return "Not reported";
  const hours = numeric / 3600;
  if (hours < 1) return `${Math.max(0, Math.round(numeric / 60))} min`;
  return `${hours.toLocaleString(undefined, { maximumFractionDigits: 1 })} hrs`;
}

export function formatDateTime(value: unknown): string {
  const text = asText(value);
  if (!text) return "Not reported";
  const date = new Date(text);
  return Number.isNaN(date.getTime()) ? "Not reported" : date.toLocaleString();
}

export function formatRelativeTime(value: unknown): string {
  const text = asText(value);
  if (!text) return "Never";
  const date = new Date(text);
  if (Number.isNaN(date.getTime())) return "Never";
  const elapsed = Math.max(0, Date.now() - date.getTime());
  const minutes = Math.floor(elapsed / 60_000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function formatList(value: unknown): string {
  if (Array.isArray(value)) {
    const items = value.map(asText).filter((item): item is string => Boolean(item));
    return items.length ? items.join(", ") : "Not reported";
  }
  return formatData(value, "Not reported");
}

export function clampPercent(value: unknown): number | null {
  const numeric = asNumber(value);
  return numeric === null ? null : Math.max(0, Math.min(100, numeric));
}
