from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

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


@router.get("/agent.zip")
def agent_package() -> StreamingResponse:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for filename in AGENT_FILES:
            path = AGENT_ROOT / filename
            if not path.exists():
                raise HTTPException(status_code=500, detail=f"Missing agent file: {filename}")
            archive.write(path, filename)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="pc-sentinel-agent.zip"'},
    )


@router.get("/command", dependencies=[Depends(require_admin)])
def install_command(request: Request, settings: Settings = Depends(get_settings)) -> dict:
    api_base_url = str(request.base_url).rstrip("/")
    token = create_install_token(settings)
    install_url = f"{api_base_url}/api/installer/install.ps1?token={token}"
    command = (
        'powershell -NoProfile -ExecutionPolicy Bypass -Command '
        f'"Invoke-WebRequest -UseBasicParsing {powershell_literal(install_url)} '
        r'-OutFile $env:TEMP\pc-sentinel-install.ps1; '
        f'powershell -ExecutionPolicy Bypass -File $env:TEMP\\pc-sentinel-install.ps1 -ApiBaseUrl {powershell_literal(api_base_url)}"'
    )
    return {"command": command, "expires_hours": INSTALL_TOKEN_EXPIRY_HOURS}


@router.get("/install.ps1")
def install_script(
    request: Request,
    token: str | None = Query(default=None),
    settings: Settings = Depends(get_settings),
) -> Response:
    api_base_url = str(request.base_url).rstrip("/")
    package_url = f"{api_base_url}/api/installer/agent.zip"
    agent_api_key_default = ""
    if token:
        validate_install_token(token, settings)
        agent_api_key_default = settings.agent_api_key
    script = f"""param(
  [string]$AgentApiKey = {powershell_literal(agent_api_key_default)},
  [string]$ApiBaseUrl = "{api_base_url}",
  [string]$PackageUrl = "{package_url}",
  [string]$InstallDir = "$env:ProgramData\\PCSentinel\\agent"
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {{
  Write-Host "[PC Sentinel] $Message"
}}

function Update-ProcessPath {{
  $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
  $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
  $env:Path = @($machinePath, $userPath) -join ";"
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

if (-not $AgentApiKey) {{
  throw "Agent API key is missing. Use the install command generated from the PC Sentinel dashboard."
}}

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
  throw "Python is required. Install Python 3.12, then run this installer again."
}}

Write-Step "Creating install folder"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

$zipPath = Join-Path $env:TEMP "pc-sentinel-agent.zip"
Write-Step "Downloading agent package"
Invoke-WebRequest -UseBasicParsing -Uri $PackageUrl -OutFile $zipPath

Write-Step "Extracting agent"
Expand-Archive -Force -Path $zipPath -DestinationPath $InstallDir

Write-Step "Installing Python packages"
& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $InstallDir "requirements.txt")

Write-Step "Writing agent configuration"
@"
API_BASE_URL=$ApiBaseUrl
AGENT_API_KEY=$AgentApiKey
COLLECTION_INTERVAL_SECONDS=60
"@ | Set-Content -Encoding UTF8 -Path (Join-Path $InstallDir ".env")

$taskName = "PC Sentinel Agent"
$agentPath = Join-Path $InstallDir "agent.py"
Write-Step "Creating startup task"
try {{
  $action = New-ScheduledTaskAction -Execute $python -Argument "`"$agentPath`"" -WorkingDirectory $InstallDir
  $trigger = New-ScheduledTaskTrigger -AtLogOn
  $settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 0)
  Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "PC Sentinel monitoring agent" -Force | Out-Null

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
Write-Step "Installed. This computer should appear in PC Sentinel after the first check-in."
"""
    return Response(
        content=script,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="install-pc-sentinel-agent.ps1"'},
    )
