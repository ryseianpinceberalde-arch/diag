import { Cpu, MemoryStick, RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";
import { asNumber, asText, formatBytes, formatPercent, UnknownRecord } from "../../lib/formatters";

type SortKey = "cpu" | "ram" | "name";

export function ProcessTable({ processes, refreshing, onRefresh }: { processes: UnknownRecord[]; refreshing: boolean; onRefresh: () => void }) {
  const [sort, setSort] = useState<SortKey>("cpu");
  const sorted = useMemo(() => [...processes].sort((left, right) => {
    if (sort === "name") return (asText(left.name) || "").localeCompare(asText(right.name) || "");
    if (sort === "ram") return (asNumber(right.ram_bytes) || 0) - (asNumber(left.ram_bytes) || 0);
    return (asNumber(right.cpu_percent) || 0) - (asNumber(left.cpu_percent) || 0);
  }), [processes, sort]);
  return (
    <section className="device-section">
      <div className="device-section-title">
        <div><Cpu size={18} /><span><h2>Active Processes</h2><p>Top agent-reported processes; command-line arguments are never collected.</p></span></div>
        <div className="header-actions">
          <label className="compact-select">Sort<select value={sort} onChange={(event) => setSort(event.target.value as SortKey)}><option value="cpu">CPU</option><option value="ram">RAM</option><option value="name">Process name</option></select></label>
          <button className="secondary" onClick={onRefresh} disabled={refreshing}><RefreshCw size={15} /> Refresh Processes</button>
        </div>
      </div>
      {sorted.length === 0 ? <p className="device-empty">No active processes reported.</p> : (
        <div className="table-wrap device-table"><table><thead><tr><th>Process</th><th>PID</th><th><Cpu size={14} /> CPU %</th><th><MemoryStick size={14} /> RAM</th><th>Status</th></tr></thead><tbody>
          {sorted.map((process, index) => <tr key={`${asText(process.pid) || "pid"}-${index}`}><td><strong>{asText(process.name) || "Unnamed process"}</strong></td><td>{asText(process.pid) || "Not reported"}</td><td>{formatPercent(process.cpu_percent)}</td><td>{formatBytes(process.ram_bytes)}</td><td>{asText(process.status) || "Running"}</td></tr>)}
        </tbody></table></div>
      )}
    </section>
  );
}
