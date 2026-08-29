-- Add asset-management metadata without replacing the existing monitoring schema.
create table if not exists public.departments (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  description text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.locations (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  building text,
  room text,
  description text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table public.computers
  add column if not exists display_name text,
  add column if not exists asset_tag text unique,
  add column if not exists device_type text not null default 'computer',
  add column if not exists os_version text,
  add column if not exists department_id uuid references public.departments(id) on delete set null,
  add column if not exists location_id uuid references public.locations(id) on delete set null,
  add column if not exists assigned_user_id uuid references auth.users(id) on delete set null,
  add column if not exists owner_name text,
  add column if not exists purchase_date date,
  add column if not exists warranty_start_date date,
  add column if not exists warranty_end_date date,
  add column if not exists agent_status text not null default 'waiting_for_agent',
  add column if not exists last_heartbeat timestamptz,
  add column if not exists capabilities jsonb not null default '[]'::jsonb,
  add column if not exists health_score numeric(5,2);

alter table public.registration_codes
  add column if not exists device_id uuid references public.computers(id) on delete cascade,
  add column if not exists created_by uuid references auth.users(id) on delete set null;

create index if not exists idx_computers_asset_filters
  on public.computers(status, device_type, department_id, location_id, agent_status);
create index if not exists idx_computers_last_heartbeat
  on public.computers(last_heartbeat desc);

alter table public.departments enable row level security;
alter table public.locations enable row level security;

drop policy if exists "administrators read departments" on public.departments;
create policy "administrators read departments" on public.departments for select to authenticated using (public.is_administrator());
drop policy if exists "administrators read locations" on public.locations;
create policy "administrators read locations" on public.locations for select to authenticated using (public.is_administrator());
