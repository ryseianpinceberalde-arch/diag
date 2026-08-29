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
$AgentVersion = '1.1.0'
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

function Get-DeviceType([object[]]$ChassisTypes, [int]$PCSystemType = 0) {
  $portable = @(8, 9, 10, 11, 12, 14, 18, 21, 30, 31, 32)
  foreach ($item in $ChassisTypes) {
    try { if ($portable -contains [int]$item) { return 'laptop' } } catch {}
  }
  if ($PCSystemType -in 2, 8) { return 'laptop' }
  return 'desktop'
}

function Get-MemoryType([int]$Code) {
  $types = @{ 20='DDR'; 21='DDR2'; 24='DDR3'; 26='DDR4'; 30='LPDDR4'; 34='DDR5'; 35='LPDDR5' }
  if ($types.ContainsKey($Code)) { return $types[$Code] }
  return $null
}

function Get-PowerPlan {
  try {
    $text = (& powercfg.exe /GetActiveScheme 2>$null | Out-String)
    if ($text -match '\(([^)]+)\)') { return $matches[1].Trim() }
  } catch {}
  return $null
}

function Get-WifiDetails {
  try {
    $values = @{}
    foreach ($line in (& netsh.exe wlan show interfaces 2>$null)) {
      if ($line -match '^\s*([^:]+?)\s*:\s*(.*?)\s*$') { $values[$matches[1].Trim().ToLowerInvariant()] = $matches[2].Trim() }
    }
    if (-not $values.ContainsKey('name')) { return $null }
    $signal = if ($values['signal'] -match '(\d+)') { [int]$matches[1] } else { $null }
    return [ordered]@{ name=$values['name']; ssid=$values['ssid']; signal_percent=$signal; radio_type=$values['radio type']; channel=$values['channel'] }
  } catch { return $null }
}

function Get-NetworkProbe {
  try {
    $requested = 2
    $replies = @(Test-Connection -ComputerName '1.1.1.1' -Count $requested -ErrorAction SilentlyContinue)
    $latencies = @($replies | ForEach-Object { if ($null -ne $_.ResponseTime) { [double]$_.ResponseTime } elseif ($null -ne $_.Latency) { [double]$_.Latency } })
    $latency = if ($latencies.Count) { [Math]::Round(($latencies | Measure-Object -Average).Average, 2) } else { $null }
    return [ordered]@{ internet_status=if ($replies.Count) { 'Reachable' } else { 'Unreachable' }; latency_ms=$latency; packet_loss_percent=[Math]::Round((($requested-$replies.Count)/$requested)*100, 2) }
  } catch { return [ordered]@{ internet_status='Unknown'; latency_ms=$null; packet_loss_percent=$null } }
}

function Normalize-AdapterName([string]$Name) {
  if ([string]::IsNullOrWhiteSpace($Name)) { return '' }
  return ($Name.ToLowerInvariant() -replace '[^a-z0-9]', '')
}

function Get-NetworkRates {
  try {
    $samples = (Get-Counter -Counter @('\Network Interface(*)\Bytes Received/sec', '\Network Interface(*)\Bytes Sent/sec') -SampleInterval 1 -MaxSamples 1 -ErrorAction Stop).CounterSamples
    $rates = @{}
    foreach ($sample in $samples) {
      $key = Normalize-AdapterName $sample.InstanceName
      if (-not $rates.ContainsKey($key)) { $rates[$key] = [ordered]@{ received=$null; sent=$null } }
      if ($sample.Path -match 'Bytes Received/sec') { $rates[$key].received = [double]$sample.CookedValue }
      if ($sample.Path -match 'Bytes Sent/sec') { $rates[$key].sent = [double]$sample.CookedValue }
    }
    return $rates
  } catch { return @{} }
}

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
  $board = Get-CimSafe 'Win32_BaseBoard' | Select-Object -First 1
  $enclosure = Get-CimSafe 'Win32_SystemEnclosure' | Select-Object -First 1
  $cpu = Get-CimSafe 'Win32_Processor' | Select-Object -First 1
  $memoryModules = Get-CimSafe 'Win32_PhysicalMemory'
  $memoryArray = Get-CimSafe 'Win32_PhysicalMemoryArray' | Select-Object -First 1
  $uptime = if ($os) { [int64](([DateTime]::UtcNow) - $os.LastBootUpTime.ToUniversalTime()).TotalSeconds } else { $null }
  $cpuUsage = try { [Math]::Round([Math]::Min(100, (Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 1).CounterSamples[0].CookedValue), 2) } catch { $null }
  $memory = if ($os) { [int64]$os.TotalVisibleMemorySize * 1024 } else { $null }
  $freeMemory = if ($os) { [int64]$os.FreePhysicalMemory * 1024 } else { $null }
  $storagePhysical = Get-CimSafe 'MSFT_PhysicalDisk' 'root/Microsoft/Windows/Storage'
  $disks = foreach ($disk in (Get-CimSafe 'Win32_LogicalDisk' | Where-Object DriveType -eq 3)) {
    $total = if ($null -ne $disk.Size) { [int64]$disk.Size } else { $null }
    $free = if ($null -ne $disk.FreeSpace) { [int64]$disk.FreeSpace } else { $null }
    $partition = try { Get-CimAssociatedInstance -InputObject $disk -Association Win32_LogicalDiskToPartition -ErrorAction Stop | Select-Object -First 1 } catch { $null }
    $physical = if ($partition) { try { Get-CimAssociatedInstance -InputObject $partition -Association Win32_DiskDriveToDiskPartition -ErrorAction Stop | Select-Object -First 1 } catch { $null } } else { $null }
    $storageDisk = if ($physical) { $storagePhysical | Where-Object { [string]$_.DeviceId -eq [string]$physical.Index } | Select-Object -First 1 } else { $null }
    $mediaType = if ($storageDisk -and [int]$storageDisk.BusType -eq 17) { 'NVMe SSD' } elseif ($storageDisk -and [int]$storageDisk.MediaType -eq 4) { 'SSD' } elseif ($storageDisk -and [int]$storageDisk.MediaType -eq 3) { 'HDD' } elseif ($physical.Model -match 'NVMe') { 'NVMe SSD' } elseif ($physical.Model -match 'SSD') { 'SSD' } else { $null }
    $smart = if ($storageDisk) { switch ([int]$storageDisk.HealthStatus) { 0 {'Healthy'} 1 {'Warning'} 2 {'Unhealthy'} default {'Unknown'} } } elseif ($physical) { $physical.Status } else { $null }
    [ordered]@{ drive_letter=$disk.DeviceID; volume_label=$disk.VolumeName; partition_label=if ($partition) { $partition.Name } else { $null }; filesystem=$disk.FileSystem; drive_type=$mediaType; disk_model=if ($physical) { $physical.Model } else { $null }; total_bytes=$total; free_bytes=$free; used_bytes=if ($null -ne $total -and $null -ne $free) { $total-$free } else { $null }; usage_percent=if ($total -and $null -ne $free) { [Math]::Round((($total-$free)/$total)*100,2) } else { $null }; smart_status=$smart; health=$smart }
  }
  $wifi = Get-WifiDetails
  $probe = Get-NetworkProbe
  $rates = Get-NetworkRates
  $networkAdapters = Get-CimSafe 'Win32_NetworkAdapter'
  $net = foreach ($adapter in (Get-CimSafe 'Win32_NetworkAdapterConfiguration' | Where-Object IPEnabled)) {
    $hardwareAdapter = $networkAdapters | Where-Object Index -eq $adapter.Index | Select-Object -First 1
    $rate = $rates[(Normalize-AdapterName $adapter.Description)]
    $isWifi = ($adapter.Description -match 'wireless|wi-?fi|802\.11') -or ($hardwareAdapter.NetConnectionID -match 'wi-?fi|wireless')
    $connectionType = if ($isWifi) { 'Wi-Fi' } elseif ($adapter.Description -match 'ethernet|gigabit') { 'Ethernet' } else { 'Unknown' }
    $status = if (-not $hardwareAdapter -or [int]$hardwareAdapter.NetConnectionStatus -eq 2) { 'Connected' } else { 'Disconnected' }
    [ordered]@{ adapter=$adapter.Description; interface=$hardwareAdapter.NetConnectionID; connection_type=$connectionType; status=$status; ssid=if ($isWifi -and $wifi) { $wifi.ssid } else { $null }; signal_percent=if ($isWifi -and $wifi) { $wifi.signal_percent } else { $null }; ipv4=@($adapter.IPAddress | Where-Object { $_ -match '^(\d{1,3}\.){3}\d{1,3}$' })[0]; ipv6=@($adapter.IPAddress | Where-Object { $_ -match ':' }); mac_address=$adapter.MACAddress; link_speed_bps=if ($hardwareAdapter) { $hardwareAdapter.Speed } else { $null }; default_gateway=@($adapter.DefaultIPGateway)[0]; dns_servers=@($adapter.DNSServerSearchOrder); internet_status=$probe.internet_status; latency_ms=$probe.latency_ms; packet_loss_percent=$probe.packet_loss_percent; download_mbps=if ($rate -and $null -ne $rate.received) { [Math]::Round(($rate.received*8)/1000000,3) } else { $null }; upload_mbps=if ($rate -and $null -ne $rate.sent) { [Math]::Round(($rate.sent*8)/1000000,3) } else { $null } }
  }
  $gpu = foreach ($item in (Get-CimSafe 'Win32_VideoController')) { [ordered]@{ name=$item.Name; manufacturer=$item.AdapterCompatibility; driver_version=$item.DriverVersion; memory_bytes=$item.AdapterRAM; temperature_c=$null } }
  $battery = Get-CimSafe 'Win32_Battery' | Select-Object -First 1
  $staticBattery = Get-CimSafe 'BatteryStaticData' 'root/wmi' | Select-Object -First 1
  $fullBattery = Get-CimSafe 'BatteryFullChargedCapacity' 'root/wmi' | Select-Object -First 1
  $powerPlan = Get-PowerPlan
  $batteryData = if ($battery) {
    $health = if ($staticBattery.DesignedCapacity -and $fullBattery.FullChargedCapacity) { [Math]::Round(($fullBattery.FullChargedCapacity/$staticBattery.DesignedCapacity)*100, 1) } else { $null }
    [ordered]@{ percentage=$battery.EstimatedChargeRemaining; charging=([int]$battery.BatteryStatus -in 2,6,7,8,9); status=$battery.Status; power_source=if ([int]$battery.BatteryStatus -in 2,3,6,7,8,9) { 'AC Adapter' } else { 'Battery' }; health_percent=$health; health_status=if ($null -eq $health) { $null } elseif ($health -ge 80) { 'Good' } elseif ($health -ge 60) { 'Fair' } else { 'Poor' }; power_plan=$powerPlan }
  } else { $null }
  $thermalZones = @(Get-CimSafe 'MSAcpi_ThermalZoneTemperature' 'root/wmi' | ForEach-Object { if ($_.CurrentTemperature) { ($_.CurrentTemperature/10)-273.15 } } | Where-Object { $_ -ge 1 -and $_ -le 120 })
  $cpuTemperature = if ($thermalZones.Count) { [Math]::Round(($thermalZones | Measure-Object -Maximum).Maximum, 1) } else { $null }
  $fan = Get-CimSafe 'Win32_Fan' | Select-Object -First 1
  $temperatureData = [ordered]@{ available=($null -ne $cpuTemperature); temperatureC=$cpuTemperature; cpu_temperature_c=$cpuTemperature; gpu_temperature_c=$null; thermal_health=if ($null -eq $cpuTemperature) { 'Unavailable' } elseif ($cpuTemperature -ge 90) { 'Critical' } elseif ($cpuTemperature -ge 80) { 'Warning' } elseif ($cpuTemperature -ge 70) { 'Warm' } else { 'Normal' }; fan_status=if ($fan) { $fan.Status } else { $null }; fan_speed_rpm=if ($fan -and $fan.DesiredSpeed) { [double]$fan.DesiredSpeed } else { $null }; fan_speed_percent=$null }
  $logicalCount = if ($cpu.NumberOfLogicalProcessors) { [double]$cpu.NumberOfLogicalProcessors } else { 1 }
  $processes = foreach ($p in (Get-CimSafe 'Win32_PerfFormattedData_PerfProc_Process' | Where-Object { $_.IDProcess -gt 0 -and $_.Name -notin @('_Total','Idle') } | Sort-Object @{Expression={[double]$_.PercentProcessorTime};Descending=$true}, @{Expression={[double]$_.WorkingSetPrivate};Descending=$true} | Select-Object -First 25)) { [ordered]@{ name=$p.Name; pid=[int]$p.IDProcess; cpu_percent=[Math]::Round([Math]::Min(100, ([double]$p.PercentProcessorTime/$logicalCount)), 2); ram_bytes=[int64]$p.WorkingSetPrivate; ram_usage_percent=if ($memory) { [Math]::Round(([double]$p.WorkingSetPrivate/$memory)*100,2) } else { $null }; status='Running' } }
  $deviceType = Get-DeviceType -ChassisTypes @($enclosure.ChassisTypes) -PCSystemType ([int]$cs.PCSystemType)
  $memoryType = @($memoryModules | ForEach-Object { Get-MemoryType ([int]$_.SMBIOSMemoryType) } | Where-Object { $_ } | Select-Object -Unique) -join ', '
  $system = [ordered]@{ device_id=Get-DeviceId; computer_name=$env:COMPUTERNAME; manufacturer=$cs.Manufacturer; model=$cs.Model; device_type=$deviceType; serial_number=$bios.SerialNumber; motherboard=if ($board) { "$($board.Manufacturer) $($board.Product)".Trim() } else { $null }; bios_version=if ($bios) { @($bios.BIOSVersion) -join ' ' } else { $null }; bios_release_date=if ($bios.ReleaseDate) { $bios.ReleaseDate.ToUniversalTime().ToString('o') } else { $null }; windows_version=$os.Caption; windows_build=$os.BuildNumber; os_version=$os.Version; architecture=$os.OSArchitecture; installation_date=if ($os.InstallDate) { $os.InstallDate.ToUniversalTime().ToString('o') } else { $null }; last_boot_time=if ($os) { $os.LastBootUpTime.ToUniversalTime().ToString('o') } else { $null }; uptime_seconds=$uptime; power_plan=$powerPlan }
  $memoryData = [ordered]@{ total_bytes=$memory; used_bytes=if ($memory -and $null -ne $freeMemory) { $memory-$freeMemory } else { $null }; available_bytes=$freeMemory; usage_percent=if ($memory -and $null -ne $freeMemory) { [Math]::Round((($memory-$freeMemory)/$memory)*100,2) } else { $null }; type=if ($memoryType) { $memoryType } else { $null }; speed_mhz=if ($memoryModules) { ($memoryModules | Measure-Object -Property Speed -Maximum).Maximum } else { $null }; slots_used=@($memoryModules).Count; slots_total=if ($memoryArray.MemoryDevices) { [int]$memoryArray.MemoryDevices } else { $null }; modules=@($memoryModules | ForEach-Object { [ordered]@{ manufacturer=$_.Manufacturer; part_number=([string]$_.PartNumber).Trim(); capacity_bytes=$_.Capacity; speed_mhz=$_.Speed; type=Get-MemoryType ([int]$_.SMBIOSMemoryType) } }) }
  $capabilities = @('cpu','memory','storage','network','processes','hardware')
  if ($batteryData) { $capabilities += 'battery' }
  if ($temperatureData.available) { $capabilities += 'temperature' }
  if ($temperatureData.fan_status) { $capabilities += 'fan' }
  return [ordered]@{ device_id=$system.device_id; agent_version=$AgentVersion; timestamp=Get-UtcNow; last_heartbeat=Get-UtcNow; agent_status='running'; capabilities=$capabilities; system=$system; cpu=[ordered]@{ model=$cpu.Name; manufacturer=$cpu.Manufacturer; physical_cores=$cpu.NumberOfCores; logical_processors=$cpu.NumberOfLogicalProcessors; usage_percent=$cpuUsage; max_clock_speed_mhz=$cpu.MaxClockSpeed; current_clock_speed_mhz=$cpu.CurrentClockSpeed }; memory=$memoryData; storage=@($disks); network=@($net); gpu=@($gpu); battery=$batteryData; temperature=$temperatureData; processes=@($processes); hardware_health=[ordered]@{ smart=@($disks | ForEach-Object { $_.smart_status }); temperatures=if ($temperatureData.available) { $temperatureData.thermal_health } else { $null } } }
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
