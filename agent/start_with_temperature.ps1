$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path "$PSScriptRoot\.."
$monitorExe = Join-Path $projectRoot "tools\LibreHardwareMonitor\LibreHardwareMonitor.exe"

if (-not (Test-Path -LiteralPath $monitorExe)) {
  Write-Host "LibreHardwareMonitor is missing. Download it first or ask the system administrator to install it."
  exit 1
}

Write-Host "Starting LibreHardwareMonitor for temperature sensors..."
Start-Process -FilePath $monitorExe -WorkingDirectory (Split-Path $monitorExe) -WindowStyle Minimized

Write-Host "Starting PC Sentinel agent..."
Set-Location $PSScriptRoot
python .\agent.py
