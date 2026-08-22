insert into public.computers (
  device_id, computer_name, manufacturer, model, operating_system, ip_address,
  agent_version, status, last_seen
) values (
  'DEV-SEED-001', 'Admin-Workstation-01', 'Dell Inc.', 'OptiPlex 7090',
  'Windows 11 Pro', '192.168.1.20', '0.1.0', 'online', timezone('utc', now())
) on conflict (device_id) do update set
  computer_name = excluded.computer_name,
  last_seen = excluded.last_seen,
  status = excluded.status;

with c as (
  select id from public.computers where device_id = 'DEV-SEED-001'
)
insert into public.diagnostic_readings (
  computer_id, cpu_usage, cpu_temperature, ram_usage, disk_usage,
  disk_temperature, disk_health, battery_percentage, battery_health,
  network_latency, packet_loss, uptime_seconds, recorded_at
)
select c.id, 42.5, 58.0, 61.2, 72.8, 41.0, 'ok', null, null, 18.4, 0.0, 284400,
       timezone('utc', now()) - interval '5 minutes'
from c;
