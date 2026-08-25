from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response, StreamingResponse
from jose import JWTError, jwt

from config import Settings, get_settings
from dependencies import require_admin
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/installer", tags=["installer"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AGENT_ROOT = PROJECT_ROOT / "agent"
AGENT_FILES = ("agent.py", "requirements.txt", "start_with_temperature.ps1")
AGENT_PACKAGE_VERSION = "2026-08-25-temperature-v2"
LIBRE_HARDWARE_MONITOR_URL = "https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases/download/v0.9.6/LibreHardwareMonitor.zip"
INSTALL_TOKEN_ALGORITHM = "HS256"
INSTALL_TOKEN_EXPIRY_HOURS = 24


def create_install_token(settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "purpose": "pc-sentinel-agent-install",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=INSTALL_TOKEN_EXPIRY_HOURS)).timestamp()),
        },
        settings.agent_api_key,
        algorithm=INSTALL_TOKEN_ALGORITHM,
    )


def validate_install_token(token: str, settings: Settings) -> None:
    try:
        payload = jwt.decode(token, settings.agent_api_key, algorithms=[INSTALL_TOKEN_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid installer token") from exc
    if payload.get("purpose") != "pc-sentinel-agent-install":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid installer token")


def powershell_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def installer_base_url(request: Request, settings: Settings) -> str:
    return (settings.installer_api_base_url or str(request.base_url)).rstrip("/")


def build_agent_package() -> BytesIO:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for filename in AGENT_FILES:
            path = AGENT_ROOT / filename
            if not path.exists():
                raise HTTPException(status_code=500, detail=f"Missing agent file: {filename}")
            archive.write(path, filename)
    buffer.seek(0)
    return buffer


@router.get("/agent.zip")
def agent_package() -> StreamingResponse:
    buffer = build_agent_package()
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="pc-sentinel-agent.zip"',
            "X-Agent-Package-Version": AGENT_PACKAGE_VERSION,
            "Cache-Control": "no-store",
        },
    )


@router.get("/command", dependencies=[Depends(require_admin)])
def install_command(request: Request, settings: Settings = Depends(get_settings)) -> dict:
    request_base_url = str(request.base_url).rstrip("/")
    api_base_url = installer_base_url(request, settings)
    if settings.installer_api_base_url and api_base_url != request_base_url:
        try:
            response = httpx.get(
                f"{api_base_url}/api/installer/command",
                headers={"Authorization": request.headers.get("authorization", "")},
                timeout=20,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            try:
                detail = exc.response.json().get("detail", "Remote installer command failed")
            except ValueError:
                detail = "Remote installer command failed"
            raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Could not reach online installer service") from exc

    token = create_install_token(settings)
    install_url = f"{api_base_url}/api/installer/install.ps1?token={token}"
    inner_command = (
        "$ErrorActionPreference = 'Stop'; "
        "$installer = Join-Path $env:TEMP 'pc-sentinel-install.ps1'; "
        "Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue; "
        "Write-Host '[PC Sentinel] Downloading installer...'; "
        f"Invoke-WebRequest -UseBasicParsing {powershell_literal(install_url)} -OutFile $installer; "
        "if (!(Test-Path $installer)) { throw '[PC Sentinel] Installer was not downloaded.' }; "
        "if ((Get-Item $installer).Length -eq 0) { throw '[PC Sentinel] Installer file is empty.' }; "
        "$head = Get-Content -LiteralPath $installer -TotalCount 1 -ErrorAction Stop; "
        "if ($head -match '^\\s*<!DOCTYPE html|^\\s*<html|^\\s*\\{') { throw '[PC Sentinel] Downloaded installer is not a PowerShell script.' }; "
        f"& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installer -ApiBaseUrl {powershell_literal(api_base_url)}"
    )
    command = inner_command
    return {
        "command": command,
        "expires_hours": INSTALL_TOKEN_EXPIRY_HOURS,
        "install_url": install_url,
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=INSTALL_TOKEN_EXPIRY_HOURS)).isoformat(),
    }


@router.get("/install.ps1")
def install_script(
    request: Request,
    token: str | None = Query(default=None),
    settings: Settings = Depends(get_settings),
) -> Response:
    api_base_url = installer_base_url(request, settings)
    package_url = f"{api_base_url}/api/installer/agent.zip?v={AGENT_PACKAGE_VERSION}"
    agent_api_key_default = ""
    if token:
        validate_install_token(token, settings)
        agent_api_key_default = settings.agent_api_key
    script = f"""param(
  [string]$AgentApiKey = {powershell_literal(agent_api_key_default)},
  [string]$ApiBaseUrl = "{api_base_url}",
  [string]$PackageUrl = "{package_url}",
  [string]$InstallDir = "$env:ProgramData\\PCSentinel\\agent",
  [switch]$AllowLocalhost
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {{
  Write-Host "[PC Sentinel] $Message"
}}

function Invoke-WithRetry([scriptblock]$Action, [string]$Description) {{
  for ($attempt = 1; $attempt -le 3; $attempt++) {{
    try {{
      if ($attempt -gt 1) {{
        Write-Step "$Description retry $attempt/3"
        Start-Sleep -Seconds (3 * $attempt)
      }}
      return & $Action
    }} catch {{
      if ($attempt -eq 3) {{
        throw
      }}
      Write-Step "$Description failed. Server may be waking up."
    }}
  }}
}}

function Assert-DownloadedFile([string]$Path, [string]$Kind) {{
  if (!(Test-Path $Path)) {{
    throw "$Kind was not downloaded."
  }}
  if ((Get-Item $Path).Length -eq 0) {{
    throw "$Kind file is empty."
  }}
  $firstLine = Get-Content -LiteralPath $Path -TotalCount 1 -ErrorAction SilentlyContinue
  if ($firstLine -match "^\\s*<!DOCTYPE html|^\\s*<html|^\\s*\\{{") {{
    throw "$Kind download returned an error page instead of the expected file."
  }}
}}

function Normalize-Url([string]$Value) {{
  if ([string]::IsNullOrWhiteSpace($Value)) {{
    return ""
  }}

  $trimmed = $Value.Trim()
  if ($trimmed -match "^\\[(https?://[^\\]]+)\\]\\(") {{
    $trimmed = $Matches[1]
  }} elseif ($trimmed -match "(https?://[^\\s\\)]+)") {{
    $trimmed = $Matches[1]
  }}

  return $trimmed.TrimEnd("/")
}}

function Test-LocalApiUrl([string]$Value) {{
  return $Value -match "localhost" -or $Value -match "127\\.0\\.0\\.1"
}}

function Update-ProcessPath {{
  $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
  $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
  $env:Path = @($machinePath, $userPath) -join ";"
}}

function Test-IsAdministrator {{
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($identity)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}}

function Resolve-Python {{
  $candidates = @(
    @{{ Command = "py"; Arguments = @("-3.12") }},
    @{{ Command = "python"; Arguments = @() }},
    @{{ Command = "python3"; Arguments = @() }}
  )

  foreach ($candidate in $candidates) {{
    $command = Get-Command $candidate.Command -ErrorAction SilentlyContinue
    if (-not $command) {{
      continue
    }}

    try {{
      $probe = & $command.Source @($candidate.Arguments) -c "import sys; print(str(sys.version_info.major) + '.' + str(sys.version_info.minor)); print(sys.executable)" 2>$null
      if ($LASTEXITCODE -ne 0 -or $probe.Count -lt 2) {{
        continue
      }}

      $version = [version]$probe[0]
      $path = [string]$probe[1]
      if ($version -ge [version]"3.12" -and (Test-Path $path)) {{
        return (Get-Item $path).FullName
      }}
    }} catch {{
      continue
    }}
  }}

  return $null
}}

function Install-PythonFromPythonOrg {{
  $installerUrl = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
  $installerPath = Join-Path $env:TEMP "python-3.12.10-amd64.exe"
  $installScope = "InstallAllUsers=0"
  if (Test-IsAdministrator) {{
    $installScope = "InstallAllUsers=1"
  }}

  Write-Step "Downloading Python installer"
  Invoke-WebRequest -UseBasicParsing -Uri $installerUrl -OutFile $installerPath

  Write-Step "Installing Python from python.org"
  $process = Start-Process -FilePath $installerPath -ArgumentList @("/quiet", $installScope, "PrependPath=1", "Include_launcher=1", "Include_pip=1") -Wait -PassThru
  if (@(0, 3010) -notcontains $process.ExitCode) {{
    throw "Python installer failed with exit code $($process.ExitCode)."
  }}

  Update-ProcessPath
}}

if (-not $AgentApiKey) {{
  throw "Agent API key is missing. Use the install command generated from the PC Sentinel dashboard."
}}

$ApiBaseUrl = Normalize-Url $ApiBaseUrl
if ([string]::IsNullOrWhiteSpace($ApiBaseUrl)) {{
  $ApiBaseUrl = "{api_base_url}"
}}
$PackageUrl = Normalize-Url $PackageUrl
if ([string]::IsNullOrWhiteSpace($PackageUrl)) {{
  $PackageUrl = "$ApiBaseUrl/api/installer/agent.zip?v={AGENT_PACKAGE_VERSION}"
}}
if ((Test-LocalApiUrl $ApiBaseUrl) -and -not $AllowLocalhost) {{
  throw "[PC Sentinel] Invalid production API server: $ApiBaseUrl"
}}

Write-Host "========================================="
Write-Host "           PC SENTINEL INSTALLER"
Write-Host "========================================="
Write-Step "[1/8] Connecting to PC Sentinel server"
Write-Step "API Server: $ApiBaseUrl"
Invoke-WithRetry {{ Invoke-WebRequest -UseBasicParsing -Uri "$ApiBaseUrl/api/health" -TimeoutSec 20 | Out-Null }} "Health check"
Write-Step "Server reachable."

Write-Step "[2/8] Checking Python runtime"
$python = Resolve-Python
if (-not $python) {{
  $winget = Get-Command winget -ErrorAction SilentlyContinue
  if ($winget) {{
    Write-Step "Installing Python with winget"
    winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    Update-ProcessPath
    $python = Resolve-Python
  }}
}}

if (-not $python) {{
  Install-PythonFromPythonOrg
  $python = Resolve-Python
}}

if (-not $python) {{
  throw "Python is required. Install Python 3.12, then run this installer again."
}}

Write-Step "Creating install folder"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

$zipPath = Join-Path $env:TEMP "pc-sentinel-agent.zip"
Write-Step "[3/8] Downloading agent package"
Invoke-WithRetry {{ Invoke-WebRequest -UseBasicParsing -Uri $PackageUrl -OutFile $zipPath -TimeoutSec 60 }} "Agent download"
Assert-DownloadedFile $zipPath "Agent package"

Write-Step "[4/8] Extracting agent"
Expand-Archive -Force -Path $zipPath -DestinationPath $InstallDir

Write-Step "[5/8] Installing Python packages"
& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $InstallDir "requirements.txt")

Write-Step "[6/8] Installing hardware sensor support"
$lhmDir = Join-Path $InstallDir "LibreHardwareMonitor"
$lhmZipPath = Join-Path $env:TEMP "LibreHardwareMonitor.zip"
New-Item -ItemType Directory -Force -Path $lhmDir | Out-Null
Invoke-WithRetry {{ Invoke-WebRequest -UseBasicParsing -Uri {powershell_literal(LIBRE_HARDWARE_MONITOR_URL)} -OutFile $lhmZipPath -TimeoutSec 90 }} "LibreHardwareMonitor download"
Assert-DownloadedFile $lhmZipPath "LibreHardwareMonitor package"
Expand-Archive -Force -Path $lhmZipPath -DestinationPath $lhmDir
$lhmDllPath = Join-Path $lhmDir "LibreHardwareMonitorLib.dll"
if (!(Test-Path $lhmDllPath)) {{
  throw "LibreHardwareMonitorLib.dll was not found after extraction."
}}

Write-Step "Writing agent configuration"
@"
API_BASE_URL=$ApiBaseUrl
AGENT_API_KEY=$AgentApiKey
COLLECTION_INTERVAL_SECONDS=60
LIBRE_HARDWARE_MONITOR_DLL=$lhmDllPath
"@ | Set-Content -Encoding UTF8 -Path (Join-Path $InstallDir ".env")
Write-Step "Configuration:"
Write-Host $ApiBaseUrl

$writtenConfig = Get-Content -LiteralPath (Join-Path $InstallDir ".env") -Raw
if ($writtenConfig -notmatch [regex]::Escape("API_BASE_URL=$ApiBaseUrl")) {{
  throw "[PC Sentinel] Agent configuration did not contain the selected API server."
}}
if ((Test-LocalApiUrl $writtenConfig) -and -not $AllowLocalhost) {{
  throw "[PC Sentinel] Agent configuration contains a localhost API URL."
}}

$taskName = "PC Sentinel Agent"
$agentPath = Join-Path $InstallDir "agent.py"

Write-Step "[7/8] Registering computer"
Push-Location $InstallDir
try {{
  & $python $agentPath --once --api-base-url $ApiBaseUrl
  $checkInExitCode = $LASTEXITCODE
}} finally {{
  Pop-Location
}}
if ($checkInExitCode -ne 0) {{
  throw "Agent could not check in. Open $InstallDir\\agent.log on this computer for details."
}}
Write-Step "Computer registered successfully."

Write-Step "[8/8] Starting agent"
try {{
  $action = New-ScheduledTaskAction -Execute $python -Argument "`"$agentPath`"" -WorkingDirectory $InstallDir
  $trigger = New-ScheduledTaskTrigger -AtLogOn
  $settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 0)
  if (Test-IsAdministrator) {{
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "PC Sentinel monitoring agent" -Force | Out-Null
  }} else {{
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "PC Sentinel monitoring agent" -Force | Out-Null
  }}

  Write-Step "Starting agent"
  Start-ScheduledTask -TaskName $taskName
}} catch {{
  Write-Step "Startup task was blocked by Windows permissions; creating user startup launcher instead"
  $startupDir = [Environment]::GetFolderPath("Startup")
  $cmdPath = Join-Path $startupDir "pc-sentinel-agent.cmd"
  @"
@echo off
cd /d "$InstallDir"
start "" /min "$python" "$agentPath"
"@ | Set-Content -Encoding ASCII -Path $cmdPath

  Write-Step "Starting agent without scheduled task"
  Start-Process -FilePath $python -ArgumentList "`"$agentPath`"" -WorkingDirectory $InstallDir -WindowStyle Hidden
}}
Write-Host "========================================="
Write-Host "PC SENTINEL INSTALLED SUCCESSFULLY"
Write-Host "========================================="
Write-Host "Computer: $env:COMPUTERNAME"
Write-Host "Server: $ApiBaseUrl"
Write-Host "Status: ONLINE"
"""
    return Response(
        content=script,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="install-pc-sentinel-agent.ps1"'},
    )
