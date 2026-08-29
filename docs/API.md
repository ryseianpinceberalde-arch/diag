# API overview

Dashboard endpoints require a Supabase bearer token. Agent registration uses a one-time hashed registration code; telemetry and heartbeat use the returned device bearer token. The service-role key is never sent to the browser or agent.

Agent endpoints:

- `POST /api/agent/register`
- `POST /api/agent/heartbeat`
- `POST /api/agent/telemetry`
- `GET /api/agent/version`
- `GET /api/agent/download/powershell`

Device endpoints:

- `GET|POST /api/devices`
- `GET|PATCH|DELETE /api/devices/{id}`
- `GET /api/devices/{id}/health`
- `GET /api/devices/{id}/metrics`
- `GET /api/devices/{id}/history`
- `GET /api/devices/{id}/hardware`
- `GET /api/devices/{id}/network`
- `GET /api/devices/{id}/processes`
- `GET /api/devices/{id}/alerts`

The device-detail response includes backend health score/label, assigned-user summary, effective online/offline state, latest reading, agent inventory, alerts, prediction, and role-derived action permissions. `/api/computers/*` remains an equivalent compatibility path.

Diagnostics and operations endpoints:

- `GET /api/diagnostics`
- `GET /api/diagnostics/{id}`
- `PATCH /api/diagnostics/{id}`
- `POST /api/diagnostics/{id}/ticket`
- `GET|POST /api/tickets`
- `GET|PATCH /api/tickets/{id}`
- `GET|POST /api/maintenance/records`
- `PATCH /api/maintenance/records/{id}`
- `GET|POST /api/departments`
- `PATCH /api/departments/{id}`
- `GET|POST /api/locations`
- `PATCH /api/locations/{id}`
- `GET /api/audit-logs`

The original `/api/agents`, `/api/computers`, `/api/readings`, `/api/alerts`, `/api/maintenance`, and `/api/reports` routes remain available.
