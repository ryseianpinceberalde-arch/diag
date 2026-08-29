# PC Sentinel architecture

The application keeps the existing React/Vite dashboard, FastAPI API, and Supabase PostgreSQL/authentication boundary.

```text
Windows PowerShell agent
  -> HTTPS /api/agent/register
  -> HTTPS /api/agent/heartbeat and /api/agent/telemetry
  -> FastAPI validation and token authentication
  -> Supabase computers + diagnostic_readings + alerts + maintenance_tickets
  -> React dashboard and Recharts history views
```

`/api/agents/*`, `/api/computers/*`, and `/api/devices/*` are retained as compatibility paths. Static device inventory lives on `computers`; changing readings live in `diagnostic_readings`; the latest full hardware snapshot is kept in `agent_inventory`.

The backend lifespan performs a lightweight stale-heartbeat sweep every ten seconds. Dashboard reads also calculate effective status so stale devices remain accurate even before the next sweep.
