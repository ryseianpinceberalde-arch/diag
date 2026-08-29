-- Align the default heartbeat/offline windows with the Windows agent contract.
update public.app_settings
set value = '120'::jsonb
where key = 'offline_after_seconds' and value = '300'::jsonb;

update public.app_settings
set value = '10'::jsonb
where key = 'agent_reporting_interval_seconds' and value = '60'::jsonb;
