export function StatusBadge({ value }: { value?: string | null }) {
  const status = value ?? "offline";
  return <span className={`badge ${status}`}>{status}</span>;
}
