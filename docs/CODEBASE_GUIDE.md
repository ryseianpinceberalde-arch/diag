# PC Sentinel Codebase Guide

This file is the **code file guide** (also called a codebase map). It labels the project's source files and explains their purpose. It does not copy the source code into this document; the actual code stays in the files listed below.

## How the system fits together

```text
Windows agent
  -> HTTPS requests
FastAPI backend
  -> Supabase authentication and PostgreSQL
React dashboard
  -> HTTPS API requests
RustDesk client (optional remote support)
```

- The Python agent collects computer status and sends readings and heartbeats to the backend.
- The FastAPI backend checks requests, applies permissions, handles device and dashboard features, and reads or writes Supabase data.
- The React/Vite frontend provides the logged-in dashboard.
- The Windows PowerShell agent under `agents/windows` is a separate legacy agent implementation. The online Python installer packages `agent/agent.py`.
- RustDesk provides remote desktop and file transfer. PC Sentinel saves each computer's RustDesk ID and opens the RustDesk application; it does not stream the remote screen itself.

## Repository and deployment files

| File | Label / purpose |
| --- | --- |
| [`README.md`](../README.md) | Main setup, run, installation, and testing instructions. |
| [`package.json`](../package.json) | Root frontend build command used by Cloudflare Pages. |
| [`wrangler.toml`](../wrangler.toml) | Cloudflare Pages/Workers static asset configuration. |
| [`render.yaml`](../render.yaml) | Render web service setup and names of required environment variables. Values are supplied in Render, not stored here. |
| [`pytest.ini`](../pytest.ini) | Root pytest discovery and test settings. |
| [`.env.example`](../.env.example) | Example root development environment settings; contains placeholders, not live credentials. |
| [`scripts/copy_frontend_dist.mjs`](../scripts/copy_frontend_dist.mjs) | Copies the built frontend files into the location expected by deployment. |
| [`scripts/apply_gpu_fan_migration.ps1`](../scripts/apply_gpu_fan_migration.ps1) | PowerShell helper for applying the GPU/fan database migration. |
| [`supabase/seed/development_seed.sql`](../supabase/seed/development_seed.sql) | Optional development data for local database setup. |

## Backend: FastAPI application

### Startup, configuration, and request handling

| File | Label / purpose |
| --- | --- |
| [`backend/main.py`](../backend/main.py) | Creates the FastAPI app, installs middleware, mounts routes, and starts the periodic offline-device sweep. |
| [`backend/config.py`](../backend/config.py) | Loads and validates backend settings from environment variables. |
| [`backend/database.py`](../backend/database.py) | Creates the Supabase clients used by backend routes and services. |
| [`backend/dependencies.py`](../backend/dependencies.py) | Authentication, role checks, and shared FastAPI dependencies. |
| [`backend/.env.example`](../backend/.env.example) | Backend environment variable template. Add real values through local environment settings or Render. |
| [`backend/requirements.txt`](../backend/requirements.txt) | Python packages required by the API. |
| [`backend/middleware/errors.py`](../backend/middleware/errors.py) | Converts application exceptions into consistent HTTP responses. |
| [`backend/middleware/rate_limit.py`](../backend/middleware/rate_limit.py) | Applies request limits to the API. |

### API routes

| File | Label / purpose |
| --- | --- |
| [`backend/routers/health.py`](../backend/routers/health.py) | Public API health check. |
| [`backend/routers/agents.py`](../backend/routers/agents.py) | Agent registration, authentication, heartbeat, telemetry, and agent version/download routes. |
| [`backend/routers/ingestion.py`](../backend/routers/ingestion.py) | Receives readings and events from agents. |
| [`backend/routers/installer.py`](../backend/routers/installer.py) | Builds the downloadable Python agent package and Windows installer script; validates time-limited installer links. |
| [`backend/routers/computers.py`](../backend/routers/computers.py) | Computer inventory, details, permissions, reports, agent actions, and RustDesk remote-support configuration/launch links. Also serves the compatible `/devices` routes. |
| [`backend/routers/dashboard.py`](../backend/routers/dashboard.py) | Dashboard summary and overview data. |
| [`backend/routers/diagnostics.py`](../backend/routers/diagnostics.py) | Diagnostic findings and related actions. |
| [`backend/routers/alerts.py`](../backend/routers/alerts.py) | Alert listing and alert updates. |
| [`backend/routers/tickets.py`](../backend/routers/tickets.py) | Repair ticket creation, listing, and updates. |
| [`backend/routers/maintenance.py`](../backend/routers/maintenance.py) | Maintenance records. |
| [`backend/routers/organization.py`](../backend/routers/organization.py) | Department and location management. |
| [`backend/routers/reports.py`](../backend/routers/reports.py) | Report data and downloads. |
| [`backend/routers/settings.py`](../backend/routers/settings.py) | Monitoring settings read/write routes. |
| [`backend/routers/users.py`](../backend/routers/users.py) | User and role administration. |
| [`backend/routers/audit.py`](../backend/routers/audit.py) | Audit log retrieval. |
| [`backend/routers/__init__.py`](../backend/routers/__init__.py) | Python package marker for route modules. |
| [`backend/schemas/__init__.py`](../backend/schemas/__init__.py) | Python package marker for request/response schemas. |
| [`backend/schemas/models.py`](../backend/schemas/models.py) | Pydantic request and response data models used by routes. |

### Backend services

| File | Label / purpose |
| --- | --- |
| [`backend/services/status.py`](../backend/services/status.py) | Calculates effective online, connection-lost, and offline status. |
| [`backend/services/offline.py`](../backend/services/offline.py) | Marks devices offline after their heartbeat becomes stale. |
| [`backend/services/settings.py`](../backend/services/settings.py) | Loads and validates monitoring thresholds. |
| [`backend/services/health.py`](../backend/services/health.py) | Evaluates a device's hardware and operating health. |
| [`backend/services/health_score.py`](../backend/services/health_score.py) | Calculates a summarized computer health score. |
| [`backend/services/diagnostics.py`](../backend/services/diagnostics.py) | Creates diagnostic checks and findings from computer data. |
| [`backend/services/alerts.py`](../backend/services/alerts.py) | Creates or updates alerts based on diagnostics and predictions. |
| [`backend/services/prediction.py`](../backend/services/prediction.py) | Generates computer risk predictions. |
| [`backend/services/notifications.py`](../backend/services/notifications.py) | Sends configured notifications for supported events. |

### Machine-learning utilities

| File | Label / purpose |
| --- | --- |
| [`backend/ml/train_model.py`](../backend/ml/train_model.py) | Training utility for the prediction model. |
| [`backend/ml/requirements.txt`](../backend/ml/requirements.txt) | Additional packages for model training. |

## Windows monitoring agents

| File | Label / purpose |
| --- | --- |
| [`agent/agent.py`](../agent/agent.py) | Primary Python Windows agent. Collects telemetry, queues failed uploads, registers the computer, and sends independent heartbeats. |
| [`agent/requirements.txt`](../agent/requirements.txt) | Python packages installed for the primary agent. |
| [`agent/start_with_temperature.ps1`](../agent/start_with_temperature.ps1) | Windows launcher/helper for starting the Python agent with temperature monitoring support. |
| [`agent/.env.example`](../agent/.env.example) | Example local Python agent configuration. Do not put real keys in a checked-in file. |
| [`agents/windows/pc-monitoring-agent.ps1`](../agents/windows/pc-monitoring-agent.ps1) | Separate legacy PowerShell monitoring agent. It uses its own configuration, credentials, and API contract; it is not the Python installer package. |

## Frontend: React dashboard

### Build and test configuration

| File | Label / purpose |
| --- | --- |
| [`frontend/package.json`](../frontend/package.json) | Frontend dependencies and commands for tests, linting, and production build. |
| [`frontend/index.html`](../frontend/index.html) | HTML page that hosts the React application. |
| [`frontend/vite.config.ts`](../frontend/vite.config.ts) | Vite and Vitest configuration. |
| [`frontend/tsconfig.json`](../frontend/tsconfig.json) | TypeScript application settings. |
| [`frontend/tsconfig.node.json`](../frontend/tsconfig.node.json) | TypeScript settings for frontend build/configuration tools. |
| [`frontend/eslint.config.js`](../frontend/eslint.config.js) | Frontend lint rules. |
| [`frontend/.env.example`](../frontend/.env.example) | Example frontend environment values, including the public API URL. |
| [`frontend/src/main.tsx`](../frontend/src/main.tsx) | Browser entry point that mounts the React app. |
| [`frontend/src/testSetup.ts`](../frontend/src/testSetup.ts) | Shared Vitest and Testing Library setup. |
| [`frontend/src/App.tsx`](../frontend/src/App.tsx) | Login/session handling and dashboard page routes. |
| [`frontend/src/styles/global.css`](../frontend/src/styles/global.css) | Shared dashboard layout, components, and responsive styles. |
| [`frontend/src/types/models.ts`](../frontend/src/types/models.ts) | Shared TypeScript data types for API and dashboard data. |

### Frontend API helpers

| File | Label / purpose |
| --- | --- |
| [`frontend/src/lib/api.ts`](../frontend/src/lib/api.ts) | Authenticated HTTP requests to the FastAPI backend. |
| [`frontend/src/lib/supabase.ts`](../frontend/src/lib/supabase.ts) | Supabase browser client and login/session connection. |
| [`frontend/src/lib/formatters.ts`](../frontend/src/lib/formatters.ts) | Shared display formatting for dates, sizes, and readings. |
| [`frontend/src/lib/export.ts`](../frontend/src/lib/export.ts) | Browser-side report/export helpers. |
| [`frontend/src/lib/browserGuards.ts`](../frontend/src/lib/browserGuards.ts) | Browser safety and environment checks used by the UI. |

### Dashboard pages

| File | Label / purpose |
| --- | --- |
| [`frontend/src/pages/LoginPage.tsx`](../frontend/src/pages/LoginPage.tsx) | User sign-in screen. |
| [`frontend/src/pages/DashboardPage.tsx`](../frontend/src/pages/DashboardPage.tsx) | System-wide status and summary dashboard. |
| [`frontend/src/pages/ComputersPage.tsx`](../frontend/src/pages/ComputersPage.tsx) | Computer inventory and search/list view. |
| [`frontend/src/pages/ComputerDetailsPage.tsx`](../frontend/src/pages/ComputerDetailsPage.tsx) | Selected computer's telemetry, health, history, and support actions. |
| [`frontend/src/pages/LiveMonitoringPage.tsx`](../frontend/src/pages/LiveMonitoringPage.tsx) | Live monitoring view. |
| [`frontend/src/pages/DiagnosticsPage.tsx`](../frontend/src/pages/DiagnosticsPage.tsx) | Diagnostic findings and actions. |
| [`frontend/src/pages/AlertsPage.tsx`](../frontend/src/pages/AlertsPage.tsx) | Alert list and status controls. |
| [`frontend/src/pages/PredictionsPage.tsx`](../frontend/src/pages/PredictionsPage.tsx) | Risk predictions and prediction history. |
| [`frontend/src/pages/RepairTicketsPage.tsx`](../frontend/src/pages/RepairTicketsPage.tsx) | Repair ticket list and workflow. |
| [`frontend/src/pages/MaintenancePage.tsx`](../frontend/src/pages/MaintenancePage.tsx) | Maintenance records. |
| [`frontend/src/pages/OrganizationPage.tsx`](../frontend/src/pages/OrganizationPage.tsx) | Department and location management. |
| [`frontend/src/pages/AgentManagementPage.tsx`](../frontend/src/pages/AgentManagementPage.tsx) | Agent installation and update management. |
| [`frontend/src/pages/ReportsPage.tsx`](../frontend/src/pages/ReportsPage.tsx) | Reports and exports. |
| [`frontend/src/pages/AuditLogsPage.tsx`](../frontend/src/pages/AuditLogsPage.tsx) | Administrative audit history. |
| [`frontend/src/pages/UsersPage.tsx`](../frontend/src/pages/UsersPage.tsx) | User and role management. |
| [`frontend/src/pages/SettingsPage.tsx`](../frontend/src/pages/SettingsPage.tsx) | Monitoring threshold settings. |

### Shared frontend components

| File | Label / purpose |
| --- | --- |
| [`frontend/src/components/Layout.tsx`](../frontend/src/components/Layout.tsx) | Shared authenticated page layout and navigation. |
| [`frontend/src/components/Header.tsx`](../frontend/src/components/Header.tsx) | Dashboard header. |
| [`frontend/src/components/LoadingBlock.tsx`](../frontend/src/components/LoadingBlock.tsx) | Loading placeholder. |
| [`frontend/src/components/MetricCard.tsx`](../frontend/src/components/MetricCard.tsx) | Displays a single metric. |
| [`frontend/src/components/StatusBadge.tsx`](../frontend/src/components/StatusBadge.tsx) | Displays a status label. |
| [`frontend/src/components/StatusBadge.test.tsx`](../frontend/src/components/StatusBadge.test.tsx) | Status badge component test. |
| [`frontend/src/components/TemperatureBadge.tsx`](../frontend/src/components/TemperatureBadge.tsx) | Displays CPU or device temperature. |
| [`frontend/src/components/FanSpeedBadge.tsx`](../frontend/src/components/FanSpeedBadge.tsx) | Displays fan status or speed. |
| [`frontend/src/components/RiskScoreIndicator.tsx`](../frontend/src/components/RiskScoreIndicator.tsx) | Displays predicted risk level/score. |
| [`frontend/src/components/UsageProgressBar.tsx`](../frontend/src/components/UsageProgressBar.tsx) | Reusable resource-usage progress indicator. |
| [`frontend/src/components/AddComputerModal.tsx`](../frontend/src/components/AddComputerModal.tsx) | Dialog for adding/registering a computer. |

### Computer details components

| File | Label / purpose |
| --- | --- |
| [`frontend/src/components/device/types.ts`](../frontend/src/components/device/types.ts) | Types shared by computer detail components. |
| [`frontend/src/components/device/DeviceHeader.tsx`](../frontend/src/components/device/DeviceHeader.tsx) | Computer identity and header actions. |
| [`frontend/src/components/device/DeviceSummaryCards.tsx`](../frontend/src/components/device/DeviceSummaryCards.tsx) | Summary status and health cards. |
| [`frontend/src/components/device/MonitoringTabs.tsx`](../frontend/src/components/device/MonitoringTabs.tsx) | Tabs for computer monitoring sections. |
| [`frontend/src/components/device/TelemetryCards.tsx`](../frontend/src/components/device/TelemetryCards.tsx) | Current CPU, memory, disk, and network metrics. |
| [`frontend/src/components/device/TelemetryHistory.tsx`](../frontend/src/components/device/TelemetryHistory.tsx) | Historical telemetry charts. |
| [`frontend/src/components/device/TelemetryProgressBar.tsx`](../frontend/src/components/device/TelemetryProgressBar.tsx) | Resource telemetry progress display. |
| [`frontend/src/components/device/StorageVolumes.tsx`](../frontend/src/components/device/StorageVolumes.tsx) | Disk/volume details. |
| [`frontend/src/components/device/HardwareSpecifications.tsx`](../frontend/src/components/device/HardwareSpecifications.tsx) | Hardware inventory. |
| [`frontend/src/components/device/WifiDiagnostics.tsx`](../frontend/src/components/device/WifiDiagnostics.tsx) | Network and Wi-Fi diagnostics. |
| [`frontend/src/components/device/ProcessTable.tsx`](../frontend/src/components/device/ProcessTable.tsx) | Process information view. |
| [`frontend/src/components/device/DiagnosticFindings.tsx`](../frontend/src/components/device/DiagnosticFindings.tsx) | Computer-specific diagnostic findings. |
| [`frontend/src/components/device/AssetMetadataEditor.tsx`](../frontend/src/components/device/AssetMetadataEditor.tsx) | Edits asset details such as owner, location, and tags. |
| [`frontend/src/components/device/RepairTicketList.tsx`](../frontend/src/components/device/RepairTicketList.tsx) | Repair tickets for the computer. |
| [`frontend/src/components/device/MaintenanceLog.tsx`](../frontend/src/components/device/MaintenanceLog.tsx) | Maintenance records for the computer. |
| [`frontend/src/components/device/DeviceActionDialog.tsx`](../frontend/src/components/device/DeviceActionDialog.tsx) | Dialog for ticket, maintenance, remote support, and agent actions. |
| [`frontend/src/components/device/RemoteSupportPanel.tsx`](../frontend/src/components/device/RemoteSupportPanel.tsx) | Saves a computer's RustDesk ID and prepares desktop/file-transfer links. |
| [`frontend/src/components/device/RemoteSupportPanel.test.tsx`](../frontend/src/components/device/RemoteSupportPanel.test.tsx) | Tests the remote-support UI, permissions/errors, and safe RustDesk links. |

## Database schema and migrations

These SQL files define incremental Supabase/PostgreSQL schema and policy changes. Apply them in chronological order to a database; they are not application source modules.

| File | Label / purpose |
| --- | --- |
| [`supabase/migrations/202608220001_diagnostic_schema.sql`](../supabase/migrations/202608220001_diagnostic_schema.sql) | Initial diagnostic tables and schema. |
| [`supabase/migrations/202608220002_gpu_fan_metrics.sql`](../supabase/migrations/202608220002_gpu_fan_metrics.sql) | GPU and fan telemetry fields. |
| [`supabase/migrations/202608230001_operations_upgrade.sql`](../supabase/migrations/202608230001_operations_upgrade.sql) | Operational records, users, settings, auditing, and related policies. |
| [`supabase/migrations/202608290001_windows_agent.sql`](../supabase/migrations/202608290001_windows_agent.sql) | Windows-agent and device registration schema. |
| [`supabase/migrations/202608290002_monitoring_defaults.sql`](../supabase/migrations/202608290002_monitoring_defaults.sql) | Default monitoring thresholds. |
| [`supabase/migrations/202608290003_asset_management.sql`](../supabase/migrations/202608290003_asset_management.sql) | Asset metadata schema. |
| [`supabase/migrations/202608300001_operations_management.sql`](../supabase/migrations/202608300001_operations_management.sql) | Operations-management schema updates. |

## Tests

| File | Label / purpose |
| --- | --- |
| [`backend/tests/test_agent_contract.py`](../backend/tests/test_agent_contract.py) | Agent and API data contract checks. |
| [`backend/tests/test_agent_registration.py`](../backend/tests/test_agent_registration.py) | Registration behavior, defaults, and authentication. |
| [`backend/tests/test_agent_liveness.py`](../backend/tests/test_agent_liveness.py) | Independent device heartbeat, fresh timestamps, and offline race checks. |
| [`backend/tests/test_python_agent_heartbeat.py`](../backend/tests/test_python_agent_heartbeat.py) | Python agent heartbeat thread behavior. |
| [`backend/tests/test_installer_package.py`](../backend/tests/test_installer_package.py) | Agent package and generated Windows installer checks. |
| [`backend/tests/test_installer_tokens.py`](../backend/tests/test_installer_tokens.py) | Installer link token validation and signing-key separation. |
| [`backend/tests/test_remote_support.py`](../backend/tests/test_remote_support.py) | RustDesk ID validation, authorization, per-computer settings, launch links, and audit entries. |
| [`backend/tests/test_status.py`](../backend/tests/test_status.py) | Online/offline status calculations. |
| [`backend/tests/test_prediction.py`](../backend/tests/test_prediction.py) | Prediction service behavior. |
| [`backend/tests/test_health_score.py`](../backend/tests/test_health_score.py) | Health score calculations. |
| [`backend/tests/test_diagnostics_service.py`](../backend/tests/test_diagnostics_service.py) | Diagnostic service behavior. |

## Existing technical documentation

| File | Label / purpose |
| --- | --- |
| [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) | System components and data flow. |
| [`docs/API.md`](API.md) | API routes and authentication overview. |
| [`docs/AGENT.md`](AGENT.md) | Agent behavior and configuration. |
| [`docs/DIAGNOSTICS.md`](DIAGNOSTICS.md) | Diagnostic workflow and findings. |

## Where to start

- To understand the backend: `backend/main.py`, then `backend/routers/`, then `backend/services/`.
- To understand the dashboard: `frontend/src/App.tsx`, then `frontend/src/pages/`, then `frontend/src/components/`.
- To understand what runs on a monitored PC: `agent/agent.py` and `agent/requirements.txt`.
- To understand Windows database setup: `supabase/migrations/`.
- To understand deployments: `render.yaml`, `wrangler.toml`, and the environment templates. Real secrets belong in Render/Supabase settings or local environment files, never in this guide or Git.
