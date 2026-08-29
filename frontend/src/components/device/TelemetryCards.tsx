import { BatteryCharging, Cpu, MemoryStick, Network, Thermometer, Wifi } from "lucide-react";
import { asNumber, asText, formatBytes, formatData, formatMbps, formatPercent, formatTemperature, UnknownRecord } from "../../lib/formatters";
import { AppSettings, DiagnosticReading } from "../../types/models";
import { TelemetryProgressBar } from "./TelemetryProgressBar";

function TelemetryCard({ icon: Icon, title, value, status, children }: { icon: typeof Cpu; title: string; value: string; status?: string; children: React.ReactNode }) {
  return (
    <article className="sensor-card">
      <header>
        <span className="sensor-icon"><Icon size={18} /></span>
        <div><h3>{title}</h3>{status && <small>{status}</small>}</div>
        <strong>{value}</strong>
      </header>
      {children}
    </article>
  );
}

function TelemetryStat({ label, value }: { label: string; value: string }) {
  return <div className="sensor-stat"><span>{label}</span><strong>{value}</strong></div>;
}

export function CpuTelemetryCard({ reading, cpu, offline }: { reading: DiagnosticReading | null; cpu: UnknownRecord; offline: boolean }) {
  const usage = reading?.cpu_usage ?? asNumber(cpu.usage_percent);
  return (
    <TelemetryCard icon={Cpu} title="CPU Utilization" value={formatPercent(usage)} status={offline ? "Last reported" : "Live"}>
      <TelemetryProgressBar value={usage} warning={70} critical={90} label="Processor load" />
      <div className="sensor-stats">
        <TelemetryStat label="Processor Model" value={formatData(cpu.model, "Not reported")} />
        <TelemetryStat label="Cores / Threads" value={`${formatData(cpu.physical_cores, "–")} cores / ${formatData(cpu.logical_processors, "–")} threads`} />
        <TelemetryStat label="Current Clock" value={asNumber(cpu.current_clock_speed_mhz) === null ? "Not reported" : `${asNumber(cpu.current_clock_speed_mhz)} MHz`} />
        <TelemetryStat label="Maximum Clock" value={asNumber(cpu.max_clock_speed_mhz) === null ? "Not reported" : `${asNumber(cpu.max_clock_speed_mhz)} MHz`} />
      </div>
    </TelemetryCard>
  );
}

export function MemoryTelemetryCard({ reading, memory, settings, offline }: { reading: DiagnosticReading | null; memory: UnknownRecord; settings: AppSettings; offline: boolean }) {
  const usage = reading?.ram_usage ?? asNumber(memory.usage_percent);
  return (
    <TelemetryCard icon={MemoryStick} title="RAM Memory" value={formatPercent(usage)} status={offline ? "Last reported" : "Live"}>
      <TelemetryProgressBar value={usage} warning={settings.ram_warning_percent} critical={settings.ram_critical_percent} label="Memory pressure" />
      <div className="sensor-stats">
        <TelemetryStat label="Used Memory" value={formatBytes(memory.used_bytes)} />
        <TelemetryStat label="Available Free" value={formatBytes(memory.available_bytes)} />
        <TelemetryStat label="Total Capacity" value={formatBytes(memory.total_bytes)} />
        <TelemetryStat label="Memory Type / Speed" value={[asText(memory.type), asNumber(memory.speed_mhz) === null ? null : `${asNumber(memory.speed_mhz)} MHz`].filter(Boolean).join(" • ") || "Not reported"} />
      </div>
    </TelemetryCard>
  );
}

export function NetworkTelemetryCard({ network, offline }: { network: UnknownRecord; offline: boolean }) {
  const connection = asText(network.connection_type) || (asText(network.ssid) ? "Wi-Fi" : "Unknown");
  const connected = ["connected", "up"].includes((asText(network.status) || "").toLowerCase());
  return (
    <TelemetryCard icon={connection === "Wi-Fi" ? Wifi : Network} title="Network Speed" value={offline ? "Historical" : connected ? "Live" : "Disconnected"} status={connection}>
      <div className="network-speed-pair">
        <div><span>Download</span><strong>{formatMbps(network.download_mbps)}</strong></div>
        <div><span>Upload</span><strong>{formatMbps(network.upload_mbps)}</strong></div>
      </div>
      <div className="sensor-stats">
        <TelemetryStat label="Connection" value={connection} />
        <TelemetryStat label="SSID" value={formatData(network.ssid, connection === "Wi-Fi" ? "Not reported" : "Not applicable")} />
        <TelemetryStat label="Latency" value={asNumber(network.latency_ms) === null ? "Not reported" : `${asNumber(network.latency_ms)} ms`} />
        <TelemetryStat label="Packet Loss" value={formatPercent(network.packet_loss_percent)} />
      </div>
    </TelemetryCard>
  );
}

export function ThermalTelemetryCard({ reading, temperature, settings, offline }: { reading: DiagnosticReading | null; temperature: UnknownRecord; settings: AppSettings; offline: boolean }) {
  const cpuTemperature = reading?.cpu_temperature ?? asNumber(temperature.cpu_temperature_c) ?? asNumber(temperature.temperatureC);
  const gpuTemperature = reading?.gpu_temperature ?? asNumber(temperature.gpu_temperature_c);
  const fanSpeed = reading?.fan_speed_rpm ?? asNumber(temperature.fan_speed_rpm);
  const state = asText(temperature.thermal_health) || (cpuTemperature === null ? "Unavailable" : cpuTemperature >= settings.cpu_temperature_critical_c ? "Critical" : cpuTemperature >= settings.cpu_temperature_warning_c ? "Warning" : "Normal");
  return (
    <TelemetryCard icon={Thermometer} title="Thermal Sensors" value={state} status={offline ? "Last reported" : "Sensor state"}>
      <TelemetryProgressBar value={cpuTemperature} warning={settings.cpu_temperature_warning_c} critical={settings.cpu_temperature_critical_c} label="CPU temperature °C" />
      <div className="sensor-stats">
        <TelemetryStat label="CPU Temperature" value={formatTemperature(cpuTemperature)} />
        <TelemetryStat label="GPU Temperature" value={formatTemperature(gpuTemperature)} />
        <TelemetryStat label="Fan Status" value={asText(temperature.fan_status) || (fanSpeed === null ? "Not reported" : "Reported")} />
        <TelemetryStat label="Fan Speed" value={fanSpeed === null ? "Not reported" : `${fanSpeed.toLocaleString()} RPM`} />
      </div>
    </TelemetryCard>
  );
}

export function BatteryTelemetryCard({ battery, system, deviceType, reading, offline }: { battery: UnknownRecord; system: UnknownRecord; deviceType: string | null | undefined; reading: DiagnosticReading | null; offline: boolean }) {
  const laptop = (deviceType || asText(system.device_type) || "").toLowerCase().includes("laptop");
  const percentage = reading?.battery_percentage ?? asNumber(battery.percentage);
  const hasBattery = Object.keys(battery).length > 0 || percentage !== null;
  const headline = hasBattery ? formatPercent(percentage, "Not available") : laptop ? "Not available" : "Not applicable";
  const charging = battery.charging === true;
  const powerSource = asText(battery.power_source) || (!laptop ? "AC" : "Not reported");
  return (
    <TelemetryCard icon={BatteryCharging} title="Power & Battery" value={headline} status={offline ? "Last reported" : charging ? "Charging" : "Power state"}>
      <TelemetryProgressBar value={percentage} warning={25} critical={10} label="Battery capacity" inverse />
      <div className="sensor-stats">
        <TelemetryStat label="Battery" value={hasBattery ? formatPercent(percentage, "Not available") : laptop ? "Not available" : "Not applicable"} />
        <TelemetryStat label="Power Source" value={`${powerSource}${charging ? " (Charging)" : ""}`} />
        <TelemetryStat label="Battery Health" value={hasBattery ? asText(battery.health_status) || formatPercent(battery.health_percent, "Not reported") : "Not applicable"} />
        <TelemetryStat label="Power Plan" value={asText(battery.power_plan) || asText(system.power_plan) || "Not reported"} />
      </div>
    </TelemetryCard>
  );
}

export function LiveTelemetryCards({
  reading,
  cpu,
  memory,
  network,
  temperature,
  battery,
  system,
  deviceType,
  settings,
  offline,
}: {
  reading: DiagnosticReading | null;
  cpu: UnknownRecord;
  memory: UnknownRecord;
  network: UnknownRecord;
  temperature: UnknownRecord;
  battery: UnknownRecord;
  system: UnknownRecord;
  deviceType: string | null | undefined;
  settings: AppSettings;
  offline: boolean;
}) {
  return (
    <div className="sensor-grid">
      <CpuTelemetryCard reading={reading} cpu={cpu} offline={offline} />
      <MemoryTelemetryCard reading={reading} memory={memory} settings={settings} offline={offline} />
      <NetworkTelemetryCard network={network} offline={offline} />
      <ThermalTelemetryCard reading={reading} temperature={temperature} settings={settings} offline={offline} />
      <BatteryTelemetryCard battery={battery} system={system} deviceType={deviceType} reading={reading} offline={offline} />
    </div>
  );
}
