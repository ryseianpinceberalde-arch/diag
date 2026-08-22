create extension if not exists "pgcrypto";

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text,
  role text not null default 'administrator' check (role in ('administrator')),
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.computers (
  id uuid primary key default gen_random_uuid(),
  device_id text not null unique,
  computer_name text not null,
  manufacturer text,
  model text,
  operating_system text,
  ip_address inet,
  agent_version text,
  status text not null default 'offline' check (status in ('online', 'offline', 'warning', 'critical')),
  last_seen timestamptz,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.diagnostic_readings (
  id bigint generated always as identity primary key,
  computer_id uuid not null references public.computers(id) on delete cascade,
  cpu_usage numeric(5,2) check (cpu_usage between 0 and 100),
  cpu_temperature numeric(6,2),
  ram_usage numeric(5,2) check (ram_usage between 0 and 100),
  disk_usage numeric(5,2) check (disk_usage between 0 and 100),
  disk_temperature numeric(6,2),
  disk_health text,
  battery_percentage numeric(5,2) check (battery_percentage is null or battery_percentage between 0 and 100),
  battery_health numeric(5,2) check (battery_health is null or battery_health between 0 and 100),
  network_latency numeric(8,2),
  packet_loss numeric(5,2) check (packet_loss is null or packet_loss between 0 and 100),
  uptime_seconds bigint,
  recorded_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.system_events (
  id bigint generated always as identity primary key,
  computer_id uuid not null references public.computers(id) on delete cascade,
  event_type text not null,
  severity text not null check (severity in ('info', 'warning', 'error', 'critical')),
  source text,
  message text not null,
  occurred_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.alerts (
  id uuid primary key default gen_random_uuid(),
  computer_id uuid not null references public.computers(id) on delete cascade,
  category text not null,
  severity text not null check (severity in ('low', 'medium', 'high', 'critical')),
  title text not null,
  description text not null,
  status text not null default 'active' check (status in ('active', 'acknowledged', 'resolved')),
  created_at timestamptz not null default timezone('utc', now()),
  acknowledged_at timestamptz,
  resolved_at timestamptz
);

create table if not exists public.predictions (
  id uuid primary key default gen_random_uuid(),
  computer_id uuid not null references public.computers(id) on delete cascade,
  risk_score integer not null check (risk_score between 0 and 100),
  risk_level text not null check (risk_level in ('low', 'medium', 'high', 'critical')),
  suspected_component text not null,
  reasons jsonb not null default '[]'::jsonb,
  recommended_action text not null,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_computers_device_id on public.computers(device_id);
create index if not exists idx_computers_last_seen on public.computers(last_seen desc);
create index if not exists idx_readings_computer_recorded on public.diagnostic_readings(computer_id, recorded_at desc);
create index if not exists idx_events_computer_occurred on public.system_events(computer_id, occurred_at desc);
create index if not exists idx_alerts_status_created on public.alerts(status, created_at desc);
create unique index if not exists idx_alerts_open_issue
  on public.alerts(computer_id, category, title)
  where status in ('active', 'acknowledged');
create index if not exists idx_predictions_computer_created on public.predictions(computer_id, created_at desc);

alter table public.profiles enable row level security;
alter table public.computers enable row level security;
alter table public.diagnostic_readings enable row level security;
alter table public.system_events enable row level security;
alter table public.alerts enable row level security;
alter table public.predictions enable row level security;

create or replace function public.is_administrator()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.profiles
    where id = auth.uid() and role = 'administrator'
  );
$$;

drop policy if exists "administrators read profiles" on public.profiles;
create policy "administrators read profiles"
on public.profiles for select
to authenticated
using (public.is_administrator() or id = auth.uid());

drop policy if exists "administrators read computers" on public.computers;
create policy "administrators read computers"
on public.computers for select
to authenticated
using (public.is_administrator());

drop policy if exists "administrators read readings" on public.diagnostic_readings;
create policy "administrators read readings"
on public.diagnostic_readings for select
to authenticated
using (public.is_administrator());

drop policy if exists "administrators read events" on public.system_events;
create policy "administrators read events"
on public.system_events for select
to authenticated
using (public.is_administrator());

drop policy if exists "administrators read alerts" on public.alerts;
create policy "administrators read alerts"
on public.alerts for select
to authenticated
using (public.is_administrator());

drop policy if exists "administrators read predictions" on public.predictions;
create policy "administrators read predictions"
on public.predictions for select
to authenticated
using (public.is_administrator());

create or replace function public.touch_computer_status()
returns trigger
language plpgsql
as $$
begin
  update public.computers
  set last_seen = new.recorded_at, status = 'online'
  where id = new.computer_id;
  return new;
end;
$$;

drop trigger if exists tr_touch_computer_status on public.diagnostic_readings;
create trigger tr_touch_computer_status
after insert on public.diagnostic_readings
for each row execute function public.touch_computer_status();
