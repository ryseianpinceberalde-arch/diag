<#
.SYNOPSIS
  Lightweight Windows monitoring agent for the existing PC Sentinel API.
.NOTES
  The agent only reads local Windows telemetry and sends it over HTTPS. It never
  executes commands received from the server.
#>
[CmdletBinding()]
param(
  [string]$ApiBaseUrl = $env:PC_MONITORING_API_URL,
  [string]$RegistrationCode,
  [int]$IntervalSeconds = 10,
  [switch]$Register,
  [switch]$InstallAsStartupTask,
  [switch]$Run,
  [switch]$Once,
  [switch]$Uninstall
)

$ErrorActionPreference = 'Stop'
$AgentVersion = '1.0.0'
$TaskName = 'PC Monitoring Agent'
$InstallRoot = Join-Path $env:ProgramData 'PCMonitoringAgent'
$ScriptPath = Join-Path $InstallRoot 'pc-monitoring-agent.ps1'
$ConfigPath = Join-Path $InstallRoot 'agent-config.json'
$DeviceIdPath = Join-Path $InstallRoot 'device-id.txt'
$LogPath = Join-Path $InstallRoot 'logs\agent.log'

function Write-AgentLog([string]$Message, [string]$Level = 'INFO') {
  New-Item -ItemType Directory -Force -Path (Split-Path $LogPath) | Out-Null
  if ((Test-Path -LiteralPath $LogPath) -and (Get-Item -LiteralPath $LogPath).Length -gt 5MB) { Move-Item -LiteralPath $LogPath -Destination "$LogPath.1" -Force }
  Add-Content -LiteralPath $LogPath -Value "$(Get-Date -Format o) [$Level] $Message"
}

function Fail([string]$Message) { Write-Host "[ERROR] $Message" -ForegroundColor Red; Write-AgentLog $Message 'ERROR'; exit 1 }
function Get-ApiUrl { if ([string]::IsNullOrWhiteSpace($ApiBaseUrl)) { Fail 'ApiBaseUrl is required.' }; if (-not $ApiBaseUrl.StartsWith('https://', [System.StringComparison]::OrdinalIgnoreCase)) { Fail 'ApiBaseUrl must use HTTPS.' }; return $ApiBaseUrl.TrimEnd('/') }
function Get-UtcNow { return [DateTime]::UtcNow.ToString('o') }
function Get-CimSafe([string]$ClassName, [string]$Namespace = 'root/cimv2') { try { return @(Get-CimInstance -ClassName $ClassName -Namespace $Namespace -ErrorAction Stop) } catch { return @() } }
function Hash-Text([string]$Text) { $sha = [Security.Cryptography.SHA256]::Create(); try { return ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($Text))).Replace('-', '').ToLowerInvariant()) } finally { $sha.Dispose() } }

function Get-DeviceId {
  if (Test-Path -LiteralPath $ConfigPath) {
    try { $configured = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json; if ($configured.deviceId) { return [string]$configured.deviceId } } catch {}
  }
  if (Test-Path -LiteralPath $DeviceIdPath) { $id = (Get-Content -LiteralPath $DeviceIdPath -Raw).Trim(); if ($id) { return $id } }
  $machine = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Cryptography' -Name MachineGuid -ErrorAction SilentlyContinue).MachineGuid
  $bios = Get-CimSafe 'Win32_BIOS' | Select-Object -First 1
  $raw = "$env:COMPUTERNAME|$machine|$($bios.SerialNumber)"
  $id = Hash-Text $raw
  New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
  Set-Content -LiteralPath $DeviceIdPath -Value $id -NoNewline
  return $id
}

function Get-Token {
  if (-not (Test-Path -LiteralPath $ConfigPath)) { return $null }
  try { $config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json; if (-not $config.encryptedToken) { return $null }; $secure = $config.encryptedToken | ConvertTo-SecureString; $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure); try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) } } catch { Fail 'Stored credential cannot be decrypted for this Windows user.' }
}

function Save-Token([string]$Token) {
  New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
  $secure = ConvertTo-SecureString $Token -AsPlainText -Force
  [ordered]@{ deviceId = Get-DeviceId; encryptedToken = (ConvertFrom-SecureString $secure); savedAt = Get-UtcNow } | ConvertTo-Json | Set-Content -LiteralPath $ConfigPath
}

function Invoke-Api([string]$Method, [string]$Path, [object]$Body = $null, [switch]$Unauthenticated) {
  $headers = @{}
  if (-not $Unauthenticated) { $token = Get-Token; if (-not $token) { throw 'Agent is not registered.' }; $headers.Authorization = "Bearer $token" }
  $params = @{ Method = $Method; Uri = "$(Get-ApiUrl)$Path"; Headers = $headers; UseBasicParsing = $true; TimeoutSec = 20; ErrorAction = 'Stop' }
  if ($null -ne $Body) { $params.ContentType = 'application/json'; $params.Body = ($Body | ConvertTo-Json -Depth 12 -Compress) }
  return Invoke-RestMethod @params
}

function Test-Preflight {
  $uri = [Uri](Get-ApiUrl); Write-Host '[PRE-FLIGHT] Testing connectivity to backend server...'
  try { [Net.Dns]::GetHostAddresses($uri.DnsSafeHost) | Out-Null; Write-Host '1. DNS Resolution... PASS' } catch { Write-Host '1. DNS Resolution... FAIL'; Fail "DNS resolution failed for $($uri.DnsSafeHost): $($_.Exception.Message)" }
  try { $client = [Net.Sockets.TcpClient]::new(); $client.Connect($uri.DnsSafeHost, 443); $client.Dispose(); Write-Host '2. TCP Socket Handshake... PASS' } catch { Write-Host '2. TCP Socket Handshake... FAIL'; Fail "TCP connection to $($uri.DnsSafeHost):443 failed: $($_.Exception.Message)" }
  try { $health = Invoke-Api 'GET' '/api/health' -Unauthenticated; if ($health.status -ne 'ok') { throw 'API returned a non-ok health status.' }; Write-Host '3. REST API Health Probe... PASS' } catch { Write-Host '3. REST API Health Probe... FAIL'; Fail "API health request failed: $($_.Exception.Message)" }
}

function Get-Inventory {
  $os = Get-CimSafe 'Win32_OperatingSystem' | Select-Object -First 1
  $cs = Get-CimSafe 'Win32_ComputerSystem' | Select-Object -First 1
  $bios = Get-CimSafe 'Win32_BIOS' | Select-Object -First 1
  $cpu = Get-CimSafe 'Win32_Processor' | Select-Object -First 1
  $uptime = if ($os) { [int64](([DateTime]::UtcNow) - $os.LastBootUpTime.ToUniversalTime()).TotalSeconds } else { $null }
  $cpuUsage = try { [Math]::Round((Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 1).CounterSamples[0].CookedValue, 2) } catch { $null }
  $memory = if ($os) { [int64]$os.TotalVisibleMemorySize * 1024 } else { $null }
  $freeMemory = if ($os) { [int64]$os.FreePhysicalMemory * 1024 } else { $null }
  $physicalDisks = Get-CimSafe 'Win32_DiskDrive'
  $disks = foreach ($disk in (Get-CimSafe 'Win32_LogicalDisk' | Where-Object DriveType -eq 3)) {
    $total = [int64]$disk.Size; $free = [int64]$disk.FreeSpace; $physical = $physicalDisks | Select-Object -First 1
    [ordered]@{ drive_letter = $disk.DeviceID; filesystem = $disk.FileSystem; disk_model = if ($physical) { $physical.Model } else { $null }; total_bytes = $total; free_bytes = $free; used_bytes = $total - $free; usage_percent = if ($total) { [Math]::Round((($total-$free)/$total)*100,2) } else { $null }; health = if ($physical) { $physical.Status } else { $null } }
  }
  $net = foreach ($adapter in (Get-CimSafe 'Win32_NetworkAdapterConfiguration' | Where-Object IPEnabled)) {
    [ordered]@{ adapter = $adapter.Description; interface = $adapter.SettingID; ipv4 = @($adapter.IPAddress | Where-Object { $_ -match '^(\d{1,3}\.){3}\d{1,3}$' })[0]; mac_address = $adapter.MACAddress; link_speed = $null; default_gateway = @($adapter.DefaultIPGateway)[0]; status = 'Up' }
  }
  $gpu = foreach ($item in (Get-CimSafe 'Win32_VideoController')) { [ordered]@{ name = $item.Name; manufacturer = $item.AdapterCompatibility; driver_version = $item.DriverVersion; memory_bytes = $item.AdapterRAM } }
  $battery = Get-CimSafe 'Win32_Battery' | Select-Object -First 1
  $batteryData = if ($battery) { [ordered]@{ percentage = $battery.EstimatedChargeRemaining; charging = ($battery.BatteryStatus -in 2,6,7,8,9); status = $battery.Status } } else { $null }
  $processes = foreach ($p in (Get-Process | ForEach-Object { try { [ordered]@{ process = $_; cpu_seconds = [double]$_.CPU } } catch {} } | Sort-Object cpu_seconds -Descending | Select-Object -First 15)) { try { [ordered]@{ name = $p.process.ProcessName; pid = $p.process.Id; cpu_seconds = $p.cpu_seconds; ram_bytes = $p.process.WorkingSet64; ram_usage_percent = if ($memory) { [Math]::Round(($p.process.WorkingSet64/$memory)*100,2) } else { $null } } } catch {} }
  $system = [ordered]@{ device_id = Get-DeviceId; computer_name = $env:COMPUTERNAME; manufacturer = $cs.Manufacturer; model = $cs.Model; serial_number = $bios.SerialNumber; windows_version = $os.Caption; windows_build = $os.BuildNumber; architecture = $os.OSArchitecture; last_boot_time = if ($os) { $os.LastBootUpTime.ToUniversalTime().ToString('o') } else { $null }; uptime_seconds = $uptime }
  return [ordered]@{ device_id = $system.device_id; agent_version = $AgentVersion; timestamp = Get-UtcNow; last_heartbeat = Get-UtcNow; agent_status = 'running'; system = $system; cpu = [ordered]@{ model = $cpu.Name; manufacturer = $cpu.Manufacturer; physical_cores = $cpu.NumberOfCores; logical_processors = $cpu.NumberOfLogicalProcessors; usage_percent = $cpuUsage; max_clock_speed_mhz = $cpu.MaxClockSpeed; current_clock_speed_mhz = $cpu.CurrentClockSpeed }; memory = [ordered]@{ total_bytes = $memory; used_bytes = if ($memory -and $freeMemory) { $memory-$freeMemory } else { $null }; available_bytes = $freeMemory; usage_percent = if ($memory -and $freeMemory) { [Math]::Round((($memory-$freeMemory)/$memory)*100,2) } else { $null } }; storage = @($disks); network = @($net); gpu = @($gpu); battery = $batteryData; temperature = [ordered]@{ available = $false; temperatureC = $null }; processes = @($processes); hardware_health = [ordered]@{ smart = $null; temperatures = $null } }
}

function Register-Agent {
  if (-not $RegistrationCode) { Fail 'RegistrationCode is required for first registration.' }
  Test-Preflight
  $inventory = Get-Inventory
  $response = Invoke-Api 'POST' '/api/agent/register' ([ordered]@{ device_id=$inventory.device_id; computer_name=$inventory.system.computer_name; manufacturer=$inventory.system.manufacturer; model=$inventory.system.model; serial_number=$inventory.system.serial_number; operating_system=$inventory.system.windows_version; agent_version=$AgentVersion; registration_code=$RegistrationCode })
  if (-not $response.token) { Fail 'Registration succeeded without receiving a device credential.' }
  Save-Token $response.token; Write-AgentLog "Registration succeeded for device $($inventory.device_id)"; Write-Host "[SUCCESS] Registered device $($response.device_id)."
}

function Install-Startup {
  $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
  if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { Write-Host '[ERROR] Administrator permission is required to install PC Monitoring Agent as a startup task.'; Write-Host 'Please run PowerShell as Administrator.'; exit 1 }
  New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
  Copy-Item -LiteralPath $PSCommandPath -Destination $ScriptPath -Force
  $action = New-ScheduledTaskAction -Execute 'PowerShell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`" -ApiBaseUrl `"$(Get-ApiUrl)`" -IntervalSeconds $IntervalSeconds -Run"
  $trigger = New-ScheduledTaskTrigger -AtStartup
  $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
  try { Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -User "$env:USERDOMAIN\$env:USERNAME" -RunLevel Highest -Force -ErrorAction Stop | Out-Null; Write-Host '[SUCCESS] Startup task installed.'; Write-AgentLog 'Startup task installed.'; Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop } catch { Write-Host "[ERROR] $($_.Exception.Message)"; Write-AgentLog "Startup task installation failed: $($_.Exception.Message)" 'ERROR'; exit 1 }
}

function Uninstall-Agent {
  try { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue } catch {}
  if (Test-Path -LiteralPath $ConfigPath) { Remove-Item -LiteralPath $ConfigPath -Force }
  if (Test-Path -LiteralPath $DeviceIdPath) { Remove-Item -LiteralPath $DeviceIdPath -Force }
  Write-Host '[SUCCESS] Agent task and local credentials removed.'
}

if ($Uninstall) { Uninstall-Agent; exit 0 }
if (-not $ApiBaseUrl) { Fail 'Use -ApiBaseUrl https://your-api.example.com.' }
if ($Register -or $RegistrationCode) { Register-Agent }
if ($InstallAsStartupTask) { Install-Startup }
if ($Once) { try { Invoke-Api 'POST' '/api/agent/telemetry' (Get-Inventory) | Out-Null; Write-Host '[SUCCESS] Telemetry sent.'; exit 0 } catch { Fail "Telemetry failed: $($_.Exception.Message)" } }
if ($Run -or (-not $Register -and -not $InstallAsStartupTask)) {
  $backoff = 0; $lastError = $null
  while ($true) {
    try { Invoke-Api 'POST' '/api/agent/telemetry' (Get-Inventory) | Out-Null; if ($backoff -gt 0) { Write-AgentLog 'Telemetry recovered.' }; $backoff = 0; $lastError = $null; Start-Sleep -Seconds ([Math]::Max(10, $IntervalSeconds)) }
    catch { $message = $_.Exception.Message; if ($message -ne $lastError -or $backoff -ge 60) { Write-AgentLog "Heartbeat failed; will retry: $message" 'WARN'; $lastError = $message }; $backoff = if ($backoff -eq 0) { 5 } else { [Math]::Min($backoff * 2, 300) }; Start-Sleep -Seconds $backoff }
  }
}
