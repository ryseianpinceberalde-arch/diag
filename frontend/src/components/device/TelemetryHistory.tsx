import { Activity } from "lucide-react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { DiagnosticReading } from "../../types/models";

export function TelemetryHistory({ readings }: { readings: DiagnosticReading[] }) {
  const data = readings.slice(-80).map((reading) => ({
    time: new Date(reading.recorded_at).toLocaleTimeString(),
    CPU: reading.cpu_usage,
    RAM: reading.ram_usage,
    Disk: reading.disk_usage,
    Temperature: reading.cpu_temperature,
  }));
  return (
    <section className="device-section">
      <div className="device-section-title"><div><Activity size={18} /><span><h2>Telemetry History</h2><p>Recent readings retained by the backend.</p></span></div></div>
      {data.length === 0 ? <p className="device-empty">No telemetry history has been reported.</p> : (
        <div className="device-chart">
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={data}>
              <XAxis dataKey="time" minTickGap={36} />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="CPU" stroke="#2563eb" dot={false} />
              <Line type="monotone" dataKey="RAM" stroke="#f59e0b" dot={false} />
              <Line type="monotone" dataKey="Disk" stroke="#e11d48" dot={false} />
              <Line type="monotone" dataKey="Temperature" stroke="#7c3aed" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
