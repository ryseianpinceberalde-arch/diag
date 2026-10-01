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
   Apply the later migration files in timestamp order as well; they add GPU/fan metrics, operations settings, the Windows agent contract, asset metadata, diagnostic findings, repair tickets, maintenance records, and notifications.
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

Open a device from Computer Inventory or browse directly to `http://localhost:5173/devices/DEVICE_UUID`. The advanced page polls the latest telemetry every 15 seconds and loads diagnostics, repair tickets, and maintenance records for that device.

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

Python agent 0.2.1 sends a lightweight heartbeat every 10 seconds independently of the diagnostic collection interval. Deploy the updated backend first, then run a freshly generated installer command on each existing PC to update its agent. The installer restarts its existing scheduled task and preserves its device ID. For installations using the user startup launcher, restart Windows after updating to replace any older running agent. Install each PC using the command; copying an installed agent folder also copies its saved device ID.

## Remote Desktop and File Access with RustDesk

1. Install the [RustDesk client](https://rustdesk.com/docs/en/client/) on the administrator's PC and each remote PC. Use compatible RustDesk server settings on both ends.
2. On the remote PC, open RustDesk and note **Your ID**. Keep RustDesk running.
3. Sign in to PC Sentinel as an administrator. Open that computer's details, then **Remote Support**.
4. Enter that PC's numeric RustDesk ID, select **Enabled**, and click **Save settings**. Repeat with the other PC's own ID.
5. Choose **Desktop control** or **File transfer**, then click the **Open RustDesk** link. Accept the browser's prompt to open the installed application. If the browser cannot open it, enter the displayed ID in RustDesk manually.
6. Approve the session on the remote PC in RustDesk and enable the required keyboard/mouse or file-transfer permissions. Edit files through the remote desktop, or download/edit/upload them through file transfer.

Remote support keeps the existing administrator-only permission. Configuration is stored per computer in the existing `app_settings` table; no migration or new service is required. Configuration changes and requests to open RustDesk are recorded in `audit_logs`. These events record launch requests, not successful sessions or file operations. RustDesk handles session authentication, permissions, and connectivity; PC Sentinel stores no RustDesk passwords. Only numeric IDs (6–16 digits, with optional spaces) are supported by this integration.

Disabling remote support in the dashboard disables its launch shortcut. End active sessions or revoke remote access in RustDesk itself. RustDesk connectivity is independent of PC Sentinel's monitoring status.

The native URL formats follow the [RustDesk URI handler](https://github.com/rustdesk/rustdesk/blob/master/flutter/lib/common.dart): `rustdesk://connect/ID` and `rustdesk://file-transfer/ID`.

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
- `GET /api/computers/{computer_id}/remote-support` (administrator only)
- `PUT /api/computers/{computer_id}/remote-support` (administrator only; `enabled`, `rustdesk_id`)
- `POST /api/computers/{computer_id}/remote-support/launch` (administrator only; mode `desktop` or `file_transfer`)
- `DELETE /api/computers/{computer_id}` (administrator only)
- `GET /api/computers/{computer_id}/history`
- `GET /api/computers/{computer_id}/predictions`
- `GET /api/alerts`
- `PATCH /api/alerts/{alert_id}/acknowledge`
- `PATCH /api/alerts/{alert_id}/resolve`
- `GET /api/diagnostics`
- `PATCH /api/diagnostics/{finding_id}`
- `POST /api/diagnostics/{finding_id}/ticket`
- `GET /api/tickets`
- `POST /api/tickets`
- `PATCH /api/tickets/{ticket_id}`
- `GET /api/maintenance/records`
- `POST /api/maintenance/records`
- `PATCH /api/maintenance/records/{record_id}`
- `GET /api/departments`
- `POST /api/departments`
- `GET /api/locations`
- `POST /api/locations`
- `GET /api/audit-logs`
- `POST /api/computers/{computer_id}/analyze`
- `GET /api/installer/command`
- `GET /api/installer/install.ps1`
- `GET /api/installer/agent.zip`
- `POST /api/agents/registration-codes` (administrator; returns a one-time registration code)
- `POST /api/agents/heartbeat` (device bearer token)
- `POST /api/agent/telemetry` (device bearer token; `/api/agents/telemetry` remains as a compatibility alias)
- `GET /api/agent/download/powershell` (administrator; generated secret-free PowerShell agent)
- `POST /api/agents/{computer_id}/regenerate-token` (administrator)

Agent endpoints require `X-Agent-Api-Key`. Administrator endpoints require a Supabase bearer token from the React app.

### PowerShell Windows agent

Create a one-time code from the authenticated dashboard session by calling `POST /api/agents/registration-codes`, then run this on the target PC in an elevated PowerShell window:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\pc-monitoring-agent.ps1 -ApiBaseUrl https://YOUR_API_DOMAIN -RegistrationCode YOUR_CODE -InstallAsStartupTask
```

The script performs DNS, TCP 443, and API health checks; registers the computer; stores the device ID and device token in a DPAPI-protected `C:\ProgramData\PCMonitoringAgent\agent-config.json`; installs the `PC Monitoring Agent` scheduled task; and sends telemetry every 10 seconds. Override the interval with `-IntervalSeconds 60`. Verify the task with `Get-ScheduledTask -TaskName 'PC Monitoring Agent'` and telemetry data with `GET /api/computers` or the Computers page.

To remove it, run `powershell -NoProfile -ExecutionPolicy Bypass -File .\pc-monitoring-agent.ps1 -ApiBaseUrl https://YOUR_API_DOMAIN -Uninstall` as the same Windows user.

## Manual Configuration Notes

- Supabase migrations must be applied to your Supabase project.
- Supabase administrator profile rows must be created manually after auth users exist.
- Windows agent sensor coverage depends on hardware, drivers, WMI permissions, and PowerShell access.
- The optional Scikit-learn folder is only for future labeled data. The live prediction behavior is explainable rule-based scoring.
