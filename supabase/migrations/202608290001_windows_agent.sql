-- Additive schema for the PowerShell Windows agent. Existing computers/readings tables remain canonical.
alter table public.computers
  add column if not exists serial_number text,
  add column if not exists windows_build text,
  add column if not exists architecture text,
  add column if not exists agent_token_hash text,
  add column if not exists agent_inventory jsonb not null default '{}'::jsonb;

create unique index if not exists idx_computers_agent_token_hash
  on public.computers(agent_token_hash) where agent_token_hash is not null;

create table if not exists public.registration_codes (
  id uuid primary key default gen_random_uuid(),
  code_hash text not null unique,
  expires_at timestamptz,
  used_at timestamptz,
  status text not null default 'active' check (status in ('active', 'used', 'revoked', 'expired')),
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_registration_codes_active on public.registration_codes(code_hash, status);

alter table public.registration_codes enable row level security;
