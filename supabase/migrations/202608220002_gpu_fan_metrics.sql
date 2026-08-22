alter table public.diagnostic_readings
  add column if not exists gpu_usage numeric(5,2) check (gpu_usage is null or gpu_usage between 0 and 100),
  add column if not exists gpu_temperature numeric(6,2),
  add column if not exists gpu_memory_usage numeric(5,2) check (gpu_memory_usage is null or gpu_memory_usage between 0 and 100),
  add column if not exists fan_speed_rpm numeric(8,2) check (fan_speed_rpm is null or fan_speed_rpm >= 0),
  add column if not exists fan_speed_percent numeric(5,2) check (fan_speed_percent is null or fan_speed_percent between 0 and 100);
