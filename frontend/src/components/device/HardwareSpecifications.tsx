import { Battery, Cpu, HardDrive, MemoryStick, Monitor, Network, ServerCog } from "lucide-react";
import { asRecord, asText, formatBytes, formatData, formatDateTime, formatList, UnknownRecord } from "../../lib/formatters";
import { Computer } from "../../types/models";
import { DeviceHardware } from "./types";

function SpecificationGroup({ title, icon: Icon, items }: { title: string; icon: typeof Cpu; items: Array<[string, string]> }) {
  return (
    <section className="spec-card">
      <h2><Icon size={17} /> {title}</h2>
      <dl>{items.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
    </section>
  );
}

export function HardwareSpecifications({ computer, hardware, network }: { computer: Computer; hardware: DeviceHardware; network: UnknownRecord[] }) {
  const { system, cpu, memory, storage, gpu, battery } = hardware;
  const firstDisk = storage[0] || {};
  const firstGpu = gpu[0] || {};
  const firstNetwork = network[0] || {};
  const modules = Array.isArray(memory.modules) ? memory.modules.map(asRecord) : [];
  return (
    <div className="spec-grid">
      <SpecificationGroup title="System" icon={ServerCog} items={[
        ["Manufacturer", computer.manufacturer || formatData(system.manufacturer)],
        ["Model", computer.model || formatData(system.model)],
        ["Serial Number", computer.serial_number || formatData(system.serial_number)],
        ["Asset Tag", computer.asset_tag || "Not assigned"],
        ["Device Type", computer.device_type || formatData(system.device_type)],
        ["Motherboard", formatData(system.motherboard)],
        ["BIOS Version", formatData(system.bios_version)],
      ]} />
      <SpecificationGroup title="Processor" icon={Cpu} items={[
        ["Processor Name", formatData(cpu.model)],
        ["Physical Cores", formatData(cpu.physical_cores)],
        ["Logical Cores", formatData(cpu.logical_processors)],
        ["Maximum Clock", cpu.max_clock_speed_mhz ? `${cpu.max_clock_speed_mhz} MHz` : "Not reported"],
      ]} />
      <SpecificationGroup title="Memory" icon={MemoryStick} items={[
        ["Installed RAM", formatBytes(memory.total_bytes)],
        ["Memory Type", formatData(memory.type)],
        ["Memory Speed", memory.speed_mhz ? `${memory.speed_mhz} MHz` : "Not reported"],
        ["Memory Slots", `${formatData(memory.slots_used, "–")} used / ${formatData(memory.slots_total, "–")} total`],
        ["Modules", modules.length ? modules.map((module) => `${formatBytes(module.capacity_bytes)} ${asText(module.type) || ""}`.trim()).join(", ") : "Not reported"],
      ]} />
      <SpecificationGroup title="Storage" icon={HardDrive} items={[
        ["Disk Model", formatData(firstDisk.disk_model)],
        ["Media Type", formatData(firstDisk.drive_type)],
        ["Capacity", formatBytes(firstDisk.total_bytes)],
        ["SMART Health", asText(firstDisk.smart_status) || asText(firstDisk.health) || "Not reported"],
        ["Volumes", storage.map((disk) => asText(disk.drive_letter)).filter(Boolean).join(", ") || "Not reported"],
      ]} />
      <SpecificationGroup title="Graphics" icon={Monitor} items={[
        ["GPU Name", formatData(firstGpu.name)],
        ["VRAM", formatBytes(firstGpu.memory_bytes)],
        ["Driver Version", formatData(firstGpu.driver_version)],
      ]} />
      <SpecificationGroup title="Network" icon={Network} items={[
        ["Primary Adapter", formatData(firstNetwork.adapter)],
        ["Connection Type", formatData(firstNetwork.connection_type)],
        ["MAC Addresses", network.map((item) => asText(item.mac_address)).filter(Boolean).join(", ") || "Not reported"],
        ["DNS Servers", formatList(firstNetwork.dns_servers)],
      ]} />
      <SpecificationGroup title="Operating System" icon={ServerCog} items={[
        ["Windows Edition", computer.operating_system || formatData(system.windows_version)],
        ["Version", computer.os_version || formatData(system.os_version)],
        ["Build", computer.windows_build || formatData(system.windows_build)],
        ["Architecture", computer.architecture || formatData(system.architecture)],
        ["Installation Date", formatDateTime(system.installation_date)],
      ]} />
      <SpecificationGroup title="Power" icon={Battery} items={[
        ["Battery", battery ? formatData(battery.status) : computer.device_type === "laptop" ? "Not available" : "Not applicable"],
        ["Power Source", battery ? formatData(battery.power_source) : "AC"],
        ["Power Plan", battery ? formatData(battery.power_plan) : formatData(system.power_plan)],
      ]} />
    </div>
  );
}
