alter table public.profiles
  add column if not exists email text,
  add column if not exists is_active boolean not null default true,
  add column if not exists updated_at timestamptz not null default timezone('utc', now());

alter table public.profiles drop constraint if exists profiles_role_check;
alter table public.profiles
  add constraint profiles_role_check check (role in ('administrator', 'technician', 'viewer'));

alter table public.computers drop constraint if exists computers_status_check;
alter table public.computers
  add constraint computers_status_check check (status in ('healthy', 'online', 'offline', 'warning', 'critical'));

alter table public.computers
  add column if not exists tags text[] not null default '{}'::text[],
  add column if not exists notes text;

create table if not exists public.app_settings (
  key text primary key,
  value jsonb not null,
  description text,
  updated_by uuid references auth.users(id) on delete set null,
  updated_at timestamptz not null default timezone('utc', now())
);

insert into public.app_settings (key, value, description)
values
  ('offline_after_seconds', '300'::jsonb, 'Seconds without heartbeat before a computer is offline'),
  ('agent_reporting_interval_seconds', '60'::jsonb, 'Default agent reporting interval'),
  ('disk_warning_percent', '85'::jsonb, 'Disk warning threshold'),
  ('disk_critical_percent', '95'::jsonb, 'Disk critical threshold'),
  ('ram_warning_percent', '85'::jsonb, 'RAM warning threshold'),
  ('ram_critical_percent', '95'::jsonb, 'RAM critical threshold'),
  ('cpu_temperature_warning_c', '80'::jsonb, 'CPU temperature warning threshold'),
  ('cpu_temperature_critical_c', '90'::jsonb, 'CPU temperature critical threshold'),
  ('packet_loss_warning_percent', '5'::jsonb, 'Packet loss warning threshold'),
  ('packet_loss_critical_percent', '10'::jsonb, 'Packet loss critical threshold'),
  ('latency_warning_ms', '200'::jsonb, 'Network latency warning threshold'),
  ('latency_critical_ms', '500'::jsonb, 'Network latency critical threshold'),
  ('risk_warning_score', '35'::jsonb, 'Operational risk warning boundary'),
  ('risk_critical_score', '75'::jsonb, 'Operational risk critical boundary'),
  ('alert_recovery_readings', '2'::jsonb, 'Normal readings required before auto-resolving an alert'),
  ('data_retention_days', '365'::jsonb, 'Telemetry retention period'),
  ('notifications_enabled', 'false'::jsonb, 'Enable alert notification delivery'),
  ('notification_recipients', '[]'::jsonb, 'Email addresses that should receive critical alerts')
on conflict (key) do nothing;

alter table public.alerts
  add column if not exists component text,
  add column if not exists alert_key text,
  add column if not exists measured_value numeric(12,2),
  add column if not exists threshold_value numeric(12,2),
  add column if not exists first_detected_at timestamptz,
  add column if not exists last_detected_at timestamptz,
  add column if not exists occurrence_count integer not null default 1,
  add column if not exists recovery_count integer not null default 0,
  add column if not exists acknowledged_by uuid references auth.users(id) on delete set null,
  add column if not exists resolved_by uuid references auth.users(id) on delete set null;

update public.alerts
set
  component = coalesce(component, category),
  alert_key = coalesce(alert_key, category || ':' || regexp_replace(lower(title), '[^a-z0-9]+', '_', 'g')),
  first_detected_at = coalesce(first_detected_at, created_at),
  last_detected_at = coalesce(last_detected_at, created_at)
where component is null
   or alert_key is null
   or first_detected_at is null
   or last_detected_at is null;

create unique index if not exists idx_alerts_active_key
  on public.alerts(computer_id, alert_key)
  where status in ('active', 'acknowledged');

create index if not exists idx_alerts_filters
  on public.alerts(status, severity, component, created_at desc);

create table if not exists public.maintenance_tickets (
  id uuid primary key default gen_random_uuid(),
  ticket_key text not null,
  computer_id uuid not null references public.computers(id) on delete cascade,
  alert_id uuid references public.alerts(id) on delete set null,
  prediction_id uuid references public.predictions(id) on delete set null,
  component text not null,
  problem_type text not null,
  title text not null,
  description text not null,
  priority text not null default 'medium' check (priority in ('low', 'medium', 'high', 'critical')),
  status text not null default 'pending' check (status in ('pending', 'in_progress', 'completed', 'cancelled')),
  assigned_technician uuid references auth.users(id) on delete set null,
  due_date date,
  technician_notes text,
  resolution_description text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  completed_at timestamptz
);

create unique index if not exists idx_maintenance_open_ticket_key
  on public.maintenance_tickets(ticket_key)
  where status in ('pending', 'in_progress');

create index if not exists idx_maintenance_filters
  on public.maintenance_tickets(status, priority, component, created_at desc);

create table if not exists public.audit_logs (
  id bigint generated always as identity primary key,
  actor_id uuid references auth.users(id) on delete set null,
  action text not null,
  target_type text,
  target_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_audit_logs_created
  on public.audit_logs(created_at desc);

create table if not exists public.agent_commands (
  id uuid primary key default gen_random_uuid(),
  computer_id uuid not null references public.computers(id) on delete cascade,
  device_id text not null,
  action text not null check (action in ('system_info', 'process_list', 'services_list', 'disk_summary', 'network_test', 'restart', 'shutdown', 'uninstall_agent')),
  status text not null default 'queued' check (status in ('queued', 'running', 'completed', 'failed', 'cancelled')),
  requested_by uuid references auth.users(id) on delete set null,
  requested_at timestamptz not null default timezone('utc', now()),
  picked_up_at timestamptz,
  completed_at timestamptz,
  result jsonb,
  error text
);

create index if not exists idx_agent_commands_device_status
  on public.agent_commands(device_id, status, requested_at);

create index if not exists idx_agent_commands_computer_requested
  on public.agent_commands(computer_id, requested_at desc);

alter table public.app_settings enable row level security;
alter table public.maintenance_tickets enable row level security;
alter table public.audit_logs enable row level security;
alter table public.agent_commands enable row level security;

drop policy if exists "administrators read settings" on public.app_settings;
create policy "administrators read settings"
on public.app_settings for select
to authenticated
using (public.is_administrator());

drop policy if exists "administrators read maintenance" on public.maintenance_tickets;
create policy "administrators read maintenance"
on public.maintenance_tickets for select
to authenticated
using (public.is_administrator());

drop policy if exists "administrators read audit logs" on public.audit_logs;
create policy "administrators read audit logs"
on public.audit_logs for select
to authenticated
using (public.is_administrator());

drop policy if exists "administrators read agent commands" on public.agent_commands;
create policy "administrators read agent commands"
on public.agent_commands for select
to authenticated
using (public.is_administrator());
