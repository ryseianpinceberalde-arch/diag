import { AlertTriangle, CheckCircle2, Wifi, WifiOff } from "lucide-react";
import { asNumber, asText, formatList, formatMbps, formatPercent, UnknownRecord } from "../../lib/formatters";
import { DiagnosticFinding } from "../../types/models";
import { StatusBadge } from "../StatusBadge";

function NetworkValue({ label, value }: { label: string; value: string }) {
  return <div className="diagnostic-value"><span>{label}</span><strong>{value}</strong></div>;
}

export function WifiDiagnostics({ network, finding }: { network: UnknownRecord[]; finding?: DiagnosticFinding }) {
  const adapter = network.find((item) => (asText(item.connection_type) || "").toLowerCase() === "wi-fi" || asText(item.ssid)) || null;
  if (!adapter) {
    return <section className="device-section device-empty-state"><WifiOff size={28} /><h2>No Wi-Fi adapter detected</h2><p>The agent did not report an active Wi-Fi interface. Ethernet adapters remain available in hardware specifications.</p></section>;
  }
  const status = finding?.severity || ((asText(adapter.status) || "").toLowerCase() === "connected" ? "healthy" : "offline");
  const evidence = finding?.evidence || [];
  return (
    <div className="wifi-layout">
      <section className="device-section">
        <div className="device-section-title">
          <div><Wifi size={18} /><span><h2>Wi-Fi Adapter & Connectivity</h2><p>Last network state reported by the Windows agent.</p></span></div>
          <StatusBadge value={status} />
        </div>
        <div className="diagnostic-grid">
          <NetworkValue label="Adapter" value={asText(adapter.adapter) || "Not reported"} />
          <NetworkValue label="Connection Status" value={asText(adapter.status) || "Unknown"} />
          <NetworkValue label="SSID" value={asText(adapter.ssid) || "Not reported"} />
          <NetworkValue label="Signal Strength" value={formatPercent(adapter.signal_percent)} />
          <NetworkValue label="IPv4" value={asText(adapter.ipv4) || "Not reported"} />
          <NetworkValue label="IPv6" value={formatList(adapter.ipv6)} />
          <NetworkValue label="MAC Address" value={asText(adapter.mac_address) || "Not reported"} />
          <NetworkValue label="Gateway" value={asText(adapter.default_gateway) || "Not reported"} />
          <NetworkValue label="DNS Servers" value={formatList(adapter.dns_servers)} />
          <NetworkValue label="Internet Status" value={asText(adapter.internet_status) || "Unknown"} />
          <NetworkValue label="Latency" value={asNumber(adapter.latency_ms) === null ? "Not reported" : `${asNumber(adapter.latency_ms)} ms`} />
          <NetworkValue label="Packet Loss" value={formatPercent(adapter.packet_loss_percent)} />
          <NetworkValue label="Download Throughput" value={formatMbps(adapter.download_mbps)} />
          <NetworkValue label="Upload Throughput" value={formatMbps(adapter.upload_mbps)} />
        </div>
      </section>
      <section className={`device-section diagnosis-card ${finding ? "has-finding" : "healthy"}`}>
        <div className="diagnosis-heading">
          {finding ? <AlertTriangle size={22} /> : <CheckCircle2 size={22} />}
          <div><span>Diagnosis</span><h2>{finding?.title || "No active network finding"}</h2></div>
        </div>
        <p>{finding?.description || "The diagnostics engine has not detected an active network threshold problem for this device."}</p>
        {evidence.length > 0 && <div><h3>Evidence</h3><pre>{JSON.stringify(evidence, null, 2)}</pre></div>}
        <div><h3>Possible Cause</h3><p>{finding?.possible_cause || "No diagnostic cause has been reported."}</p></div>
        <div><h3>Recommended Actions</h3><p>{finding?.recommendation || "Continue monitoring the adapter and gateway."}</p></div>
      </section>
    </div>
  );
}
