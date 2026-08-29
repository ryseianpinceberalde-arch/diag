# Windows monitoring agent

The agent is [agents/windows/pc-monitoring-agent.ps1](../agents/windows/pc-monitoring-agent.ps1). It uses CIM/WMI and native PowerShell only, sends read-only telemetry over HTTPS, stores its device token with Windows DPAPI, and never accepts remote commands.

It collects system identity, motherboard/BIOS data, CPU, memory modules, logical volumes and media health, GPU inventory, active network adapters, Wi-Fi state, current adapter throughput, latency and packet loss, battery/power data when present, temperature and fan data only when Windows exposes them, and at most 25 resource-heavy processes without command-line arguments.

Agent version 1.1.0 stores the full snapshot in `computers.agent_inventory`. Unsupported temperature, fan, battery, SMART, signal, and throughput fields remain `null`; the dashboard converts them to explicit unavailable/not-reported states rather than inventing readings. The agent does not run an internet speed test, so the displayed upload/download values are current adapter throughput.

Install:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\pc-monitoring-agent.ps1 -ApiBaseUrl https://YOUR_API -RegistrationCode CODE -InstallAsStartupTask
```

The agent stores configuration below `C:\ProgramData\PCMonitoringAgent`, rotates `agent.log` at 5 MB, retries network failures with exponential backoff, and supports `-Once` and `-Uninstall`.
