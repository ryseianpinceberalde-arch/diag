# Computer Diagnostic and Predictive Maintenance System

This project implements a Windows monitoring agent, a FastAPI backend, Supabase storage/auth, and a React administrator dashboard.

Architecture:

```text
Windows Monitoring Agent -> FastAPI Backend -> Supabase -> React Dashboard
```

## Project Layout

```text
backend/                 FastAPI API, Supabase service-role integration, risk scoring
agent/                   Windows monitoring agent with SQLite retry queue
frontend/                React TypeScript administrator dashboard
supabase/migrations/     Versioned database schema
supabase/seed/           Development-only seed data
tests/                   Shared test area
```

## Prerequisites

- Windows 10 or 11
- PowerShell
- Python 3.11+
- Node.js 20+
- Supabase project and Supabase CLI

## Supabase Setup

1. Create a Supabase project.
2. Copy the project URL, anon key, and service-role key.
3. Run the SQL migration in `supabase/migrations/202608220001_diagnostic_schema.sql` using the Supabase SQL editor or CLI.
4. Create an administrator user in Supabase Authentication.
5. Insert a matching profile row for that user:

```sql
insert into public.profiles (id, full_name, role)
values ('YOUR_AUTH_USER_ID', 'Administrator', 'administrator')
on conflict (id) do update set role = 'administrator';
```

Development seed data is optional and lives in `supabase/seed/development_seed.sql`. Do not run seed files in production unless you want demo rows.

## Environment Files

Create backend env:

```powershell
Copy-Item backend\.env.example backend\.env
notepad backend\.env
```

Required backend values:

```text
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
AGENT_API_KEY=
CORS_ORIGINS=http://localhost:5173
```

Create frontend env:

```powershell
Copy-Item frontend\.env.example frontend\.env
notepad frontend\.env
```

Frontend values:

```text
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
VITE_API_URL=http://localhost:8000
```

Create agent env:

```powershell
Copy-Item agent\.env.example agent\.env
notepad agent\.env
```

Agent values:

```text
API_BASE_URL=http://localhost:8000
AGENT_API_KEY=
COLLECTION_INTERVAL_SECONDS=60
```

Use the same `AGENT_API_KEY` in `backend\.env` and `agent\.env`. Never put `SUPABASE_SERVICE_ROLE_KEY` or `AGENT_API_KEY` in `frontend\.env`.

## Install Frontend Dependencies

```powershell
Set-Location frontend
npm install
Set-Location ..
```

## Install Backend Dependencies

```powershell
py -3.11 -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r backend\requirements.txt
Deactivate
```

## Install Agent Dependencies

```powershell
py -3.11 -m venv agent\.venv
agent\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r agent\requirements.txt
Deactivate
```

## Run FastAPI

```powershell
backend\.venv\Scripts\Activate.ps1
Set-Location backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

## Run React

```powershell
Set-Location frontend
npm run dev
```

Open `http://localhost:5173` and sign in with the Supabase administrator account.

## Run Windows Monitoring Agent

Open a separate elevated PowerShell window when you want WMI and Windows Event Viewer access:

```powershell
agent\.venv\Scripts\Activate.ps1
Set-Location agent
python .\agent.py
```

Unsupported hardware sensors return `null`. The local retry queue is `agent\agent_queue.sqlite3`.

For CPU/disk temperature on Windows, run the helper from an Administrator PowerShell window after LibreHardwareMonitor has been downloaded to `tools\LibreHardwareMonitor`:

```powershell
Set-Location agent
.\start_with_temperature.ps1
```

Some PCs still hide sensor values at the BIOS/driver level. In that case the dashboard hides the missing sensor while the rest of the diagnostics continue to work.

## Install Agent From Online Backend

When FastAPI is published online, another Windows computer can install the agent directly from the backend. The other computer does not need a dashboard login.

From the dashboard, open **Add Computer** and copy the generated install command. Run that command on the other Windows PC:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing 'https://YOUR_API_DOMAIN/api/installer/install.ps1?token=INSTALL_TOKEN' -OutFile $env:TEMP\pc-sentinel-install.ps1; powershell -ExecutionPolicy Bypass -File $env:TEMP\pc-sentinel-install.ps1 -ApiBaseUrl 'https://YOUR_API_DOMAIN'"
```

Only a logged-in dashboard admin can generate the temporary installer token. The installer downloads `agent.zip`, installs Python packages, writes the agent `.env`, creates a Windows startup task named `PC Sentinel Agent`, and starts the agent.

## Run Tests and Checks

Backend:

```powershell
backend\.venv\Scripts\Activate.ps1
pytest
Deactivate
```

Frontend:

```powershell
Set-Location frontend
npm test
npm run build
Set-Location ..
```

## API Summary

- `GET /api/health`
- `POST /api/agents/register`
- `POST /api/readings`
- `POST /api/events`
- `GET /api/dashboard/summary`
- `GET /api/computers`
- `GET /api/computers/{computer_id}`
- `GET /api/computers/{computer_id}/history`
- `GET /api/computers/{computer_id}/predictions`
- `GET /api/alerts`
- `PATCH /api/alerts/{alert_id}/acknowledge`
- `PATCH /api/alerts/{alert_id}/resolve`
- `POST /api/computers/{computer_id}/analyze`
- `GET /api/installer/command`
- `GET /api/installer/install.ps1`
- `GET /api/installer/agent.zip`

Agent endpoints require `X-Agent-Api-Key`. Administrator endpoints require a Supabase bearer token from the React app.

## Manual Configuration Notes

- Supabase migrations must be applied to your Supabase project.
- Supabase administrator profile rows must be created manually after auth users exist.
- Windows agent sensor coverage depends on hardware, drivers, WMI permissions, and PowerShell access.
- The optional Scikit-learn folder is only for future labeled data. The live prediction behavior is explainable rule-based scoring.
