-- Add diagnostic findings, repair tickets, maintenance records, and in-app notifications.
alter table public.profiles drop constraint if exists profiles_role_check;
alter table public.profiles
  add constraint profiles_role_check check (role in ('super_admin', 'it_admin', 'administrator', 'technician', 'department_user', 'viewer'));

create or replace function public.is_administrator()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.profiles
    where id = auth.uid() and role in ('super_admin', 'it_admin', 'administrator')
  );
$$;

alter table public.computers drop constraint if exists computers_status_check;
alter table public.computers
  add constraint computers_status_check check (status in ('healthy', 'online', 'offline', 'warning', 'critical', 'maintenance', 'waiting_for_agent'));

create table if not exists public.diagnostic_findings (
  id uuid primary key default gen_random_uuid(),
  computer_id uuid not null references public.computers(id) on delete cascade,
  alert_id uuid references public.alerts(id) on delete set null,
  finding_key text not null,
  finding_type text not null,
  component text not null,
  severity text not null default 'warning' check (severity in ('info', 'warning', 'critical')),
  title text not null,
  description text not null,
  evidence jsonb not null default '[]'::jsonb,
  possible_cause text,
  recommendation text,
  first_detected_at timestamptz not null default timezone('utc', now()),
  last_detected_at timestamptz not null default timezone('utc', now()),
  occurrence_count integer not null default 1,
  recovery_count integer not null default 0,
  status text not null default 'active' check (status in ('active', 'acknowledged', 'resolved', 'ignored')),
  resolved_at timestamptz,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create unique index if not exists idx_diagnostic_findings_active_key
  on public.diagnostic_findings(computer_id, finding_key)
  where status in ('active', 'acknowledged');
create index if not exists idx_diagnostic_findings_filters
  on public.diagnostic_findings(status, severity, component, last_detected_at desc);

alter table public.alerts
  add column if not exists finding_id uuid references public.diagnostic_findings(id) on delete set null;

create table if not exists public.repair_tickets (
  id uuid primary key default gen_random_uuid(),
  ticket_number text not null unique,
  computer_id uuid not null references public.computers(id) on delete cascade,
  diagnostic_finding_id uuid references public.diagnostic_findings(id) on delete set null,
  reported_by uuid references auth.users(id) on delete set null,
  assigned_technician_id uuid references auth.users(id) on delete set null,
  severity text not null default 'medium' check (severity in ('info', 'warning', 'critical', 'low', 'medium', 'high')),
  category text not null,
  title text not null,
  description text not null,
  status text not null default 'open' check (status in ('open', 'assigned', 'in_progress', 'waiting_for_parts', 'resolved', 'verified', 'closed', 'cancelled')),
  resolution text,
  verification_notes text,
  resolved_at timestamptz,
  verified_at timestamptz,
  closed_at timestamptz,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_repair_tickets_filters
  on public.repair_tickets(status, severity, category, created_at desc);
create index if not exists idx_repair_tickets_computer
  on public.repair_tickets(computer_id, created_at desc);
create unique index if not exists idx_repair_tickets_open_finding
  on public.repair_tickets(diagnostic_finding_id)
  where diagnostic_finding_id is not null
    and status in ('open', 'assigned', 'in_progress', 'waiting_for_parts');

create table if not exists public.maintenance_records (
  id uuid primary key default gen_random_uuid(),
  computer_id uuid not null references public.computers(id) on delete cascade,
  ticket_id uuid references public.repair_tickets(id) on delete set null,
  maintenance_type text not null default 'preventive' check (maintenance_type in ('preventive', 'corrective', 'inspection', 'cleaning', 'software', 'hardware')),
  problem_description text,
  actions_taken text,
  parts_replaced text,
  technician_id uuid references auth.users(id) on delete set null,
  started_at timestamptz,
  completed_at timestamptz,
  status text not null default 'scheduled' check (status in ('scheduled', 'in_progress', 'completed', 'cancelled')),
  notes text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_maintenance_records_filters
  on public.maintenance_records(status, maintenance_type, created_at desc);
create index if not exists idx_maintenance_records_computer
  on public.maintenance_records(computer_id, created_at desc);

create table if not exists public.notifications (
  id uuid primary key default gen_random_uuid(),
  computer_id uuid references public.computers(id) on delete cascade,
  alert_id uuid references public.alerts(id) on delete cascade,
  type text not null,
  severity text not null default 'info' check (severity in ('info', 'low', 'medium', 'high', 'warning', 'critical')),
  title text not null,
  message text not null,
  status text not null default 'unread' check (status in ('unread', 'read', 'archived')),
  created_at timestamptz not null default timezone('utc', now()),
  read_at timestamptz
);

create unique index if not exists idx_notifications_alert
  on public.notifications(alert_id)
  where alert_id is not null;
create index if not exists idx_notifications_status_created
  on public.notifications(status, created_at desc);

alter table public.diagnostic_findings enable row level security;
alter table public.repair_tickets enable row level security;
alter table public.maintenance_records enable row level security;
alter table public.notifications enable row level security;

drop policy if exists "administrators read diagnostic findings" on public.diagnostic_findings;
create policy "administrators read diagnostic findings"
on public.diagnostic_findings for select
to authenticated
using (public.is_administrator());

drop policy if exists "administrators read repair tickets" on public.repair_tickets;
create policy "administrators read repair tickets"
on public.repair_tickets for select
to authenticated
using (public.is_administrator());

drop policy if exists "administrators read maintenance records" on public.maintenance_records;
create policy "administrators read maintenance records"
on public.maintenance_records for select
to authenticated
using (public.is_administrator());

drop policy if exists "administrators read notifications" on public.notifications;
create policy "administrators read notifications"
on public.notifications for select
to authenticated
using (public.is_administrator());
