from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import platform
import signal
import socket
import sqlite3
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil
import requests
from dotenv import load_dotenv

try:
    import wmi
except Exception:
    wmi = None

AGENT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = AGENT_DIR / ".env"
DEFAULT_API_BASE_URL = "https://pc-sentinel-api.onrender.com"
load_dotenv(CONFIG_PATH, override=True)

parser = argparse.ArgumentParser(description="PC Sentinel monitoring agent")
parser.add_argument("--once", action="store_true", help="Register once and exit")
parser.add_argument("--api-base-url", default=None, help="Override the API base URL for this run")
parser.add_argument("--dev", action="store_true", help="Allow localhost API URLs for development")
ARGS, _UNKNOWN_ARGS = parser.parse_known_args()


def normalize_url(value: str | None) -> str:
    return (value or DEFAULT_API_BASE_URL).strip().rstrip("/")


def is_local_api_url(value: str) -> bool:
    lowered = value.lower()
    return "localhost" in lowered or "127.0.0.1" in lowered


API_BASE_URL = normalize_url(ARGS.api_base_url or os.getenv("API_BASE_URL") or DEFAULT_API_BASE_URL)
AGENT_API_KEY = os.getenv("AGENT_API_KEY", "")
INTERVAL = int(os.getenv("COLLECTION_INTERVAL_SECONDS", "60"))
AGENT_VERSION = "0.2.0"
QUEUE_PATH = Path(os.getenv("AGENT_QUEUE_PATH", str(AGENT_DIR / "agent_queue.sqlite3")))
DEVICE_ID_PATH = Path(os.getenv("AGENT_DEVICE_ID_PATH", str(AGENT_DIR / "device-id.txt")))
LHM_DLL_PATH = Path(os.getenv("LIBRE_HARDWARE_MONITOR_DLL", "..\\tools\\LibreHardwareMonitor\\LibreHardwareMonitorLib.dll"))
ALLOW_ACPI_TEMPERATURE_FALLBACK = os.getenv("ALLOW_ACPI_TEMPERATURE_FALLBACK", "false").lower() == "true"

logging.basicConfig(
    filename=str(AGENT_DIR / "agent.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("diagnostic-agent")
stop_requested = False

if is_local_api_url(API_BASE_URL) and not ARGS.dev:
    raise RuntimeError(f"Invalid production API URL: {API_BASE_URL}. Use --dev only for local development.")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_startup_context() -> None:
    logger.info("PC Sentinel Agent starting")
    logger.info("Agent version: %s", AGENT_VERSION)
    logger.info("Agent path: %s", Path(__file__).resolve())
    logger.info("Configuration path: %s", CONFIG_PATH)
    logger.info("API Base URL: %s", API_BASE_URL)
    logger.info("Registration endpoint: %s", f"{API_BASE_URL}/api/agents/register")
    logger.info("Readings endpoint: %s", f"{API_BASE_URL}/api/readings")


def check_api_health() -> bool:
    health_url = f"{API_BASE_URL}/api/health"
    for attempt in range(1, 4):
        try:
            response = requests.get(health_url, timeout=10)
            if response.ok:
                logger.info("API health check succeeded: %s", health_url)
                return True
            logger.warning("API health check failed server=%s status=%s body=%s", API_BASE_URL, response.status_code, response.text[:500])
        except Exception as exc:
            logger.warning("API health check failed server=%s attempt=%s error=%s", API_BASE_URL, attempt, exc)
        if attempt < 3:
            time.sleep(3 * attempt)
    return False


def stable_device_id() -> str:
    try:
        if DEVICE_ID_PATH.exists():
            existing = DEVICE_ID_PATH.read_text(encoding="utf-8").strip()
            if existing:
                return existing
        DEVICE_ID_PATH.parent.mkdir(parents=True, exist_ok=True)
        generated = str(uuid.uuid4())
        DEVICE_ID_PATH.write_text(generated, encoding="utf-8")
        return generated
    except Exception as exc:
        logger.warning("Persistent device id failed, using hardware fallback: %s", exc)

    parts = [platform.node(), str(uuid.getnode())]
    if wmi:
        try:
            conn = wmi.WMI()
            bios = next(iter(conn.Win32_BIOS()), None)
            cs = next(iter(conn.Win32_ComputerSystemProduct()), None)
            if bios and bios.SerialNumber:
                parts.append(str(bios.SerialNumber))
            if cs and cs.UUID:
                parts.append(str(cs.UUID))
        except Exception as exc:
            logger.debug("WMI device id lookup failed: %s", exc)
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def local_ip() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except Exception:
        return None


def computer_metadata() -> dict[str, Any]:
    manufacturer = model = None
    if wmi:
        try:
            system = next(iter(wmi.WMI().Win32_ComputerSystem()), None)
            manufacturer = getattr(system, "Manufacturer", None)
            model = getattr(system, "Model", None)
        except Exception as exc:
            logger.debug("WMI computer metadata failed: %s", exc)
    return {
        "device_id": stable_device_id(),
        "computer_name": platform.node(),
        "manufacturer": manufacturer,
        "model": model,
        "operating_system": f"{platform.system()} {platform.release()} {platform.version()}",
        "ip_address": local_ip(),
        "agent_version": AGENT_VERSION,
    }


def safe_temperature(label: str) -> float | None:
    label = label.lower()
    library_value = libre_hardware_monitor_library_temperature(label)
    if library_value is not None:
        return library_value
    hardware_monitor_value = hardware_monitor_temperature(label)
    if hardware_monitor_value is not None:
        return hardware_monitor_value
    try:
        sensors = psutil.sensors_temperatures(fahrenheit=False)
        candidates = []
        for name, entries in sensors.items():
            for entry in entries:
                text = f"{name} {getattr(entry, 'label', '')}".lower()
                if label in text and entry.current is not None:
                    candidates.append((text, float(entry.current)))
        selected = select_temperature_value(label, candidates)
        if selected is not None:
            return selected
    except Exception:
        pass
    if label == "cpu" and ALLOW_ACPI_TEMPERATURE_FALLBACK:
        return wmi_thermal_zone_temperature()
    return None


def safe_fan_speed_rpm() -> float | None:
    value = libre_hardware_monitor_library_sensor_value("Fan", [], [])
    if value is not None:
        return value
    return hardware_monitor_sensor_value("Fan", [], [])


def safe_fan_speed_percent() -> float | None:
    value = libre_hardware_monitor_library_sensor_value("Control", ["fan"], [])
    if value is not None:
        return value
    value = hardware_monitor_sensor_value("Control", ["fan"], [])
    if value is not None:
        return value
    return nvidia_smi_fan_speed_percent()


def hardware_monitor_temperature(label: str) -> float | None:
    if label.lower() == "cpu":
        return hardware_monitor_sensor_value("Temperature", ["cpu", "core", "package", "tctl", "tdie"], ["distance", "tjmax"])
    if label.lower() == "disk":
        return hardware_monitor_sensor_value("Temperature", ["hdd", "ssd", "nvme", "drive", "disk"], [])
    return None


def hardware_monitor_sensor_value(
    sensor_type: str,
    keywords: list[str],
    exclude_keywords: list[str],
    require_all_keywords: bool = False,
) -> float | None:
    if not wmi:
        return None
    namespaces = ("root\\LibreHardwareMonitor", "root\\OpenHardwareMonitor")
    normalized_type = sensor_type.lower()
    normalized_keywords = [keyword.lower() for keyword in keywords]
    normalized_excludes = [keyword.lower() for keyword in exclude_keywords]
    try:
        for namespace in namespaces:
            try:
                sensors = wmi.WMI(namespace=namespace).Sensor()
            except Exception:
                continue
            values = []
            named_values = []
            for sensor in sensors:
                actual_type = str(getattr(sensor, "SensorType", "") or "").lower()
                text = " ".join(
                    str(getattr(sensor, attr, "") or "")
                    for attr in ("Name", "Identifier", "Parent", "HardwareName")
                ).lower()
                value = getattr(sensor, "Value", None)
                if actual_type != normalized_type or value is None:
                    continue
                if normalized_excludes and any(keyword in text for keyword in normalized_excludes):
                    continue
                if normalized_keywords:
                    if require_all_keywords and not all(keyword in text for keyword in normalized_keywords):
                        continue
                    if not require_all_keywords and not any(keyword in text for keyword in normalized_keywords):
                        continue
                sensor_value = float(value)
                values.append(sensor_value)
                named_values.append((text, sensor_value))
            selected = select_temperature_value(normalized_keywords[0] if normalized_type == "temperature" and normalized_keywords else "", named_values)
            if selected is not None:
                return selected
            if values:
                return round(sum(values) / len(values), 2)
    except Exception as exc:
        logger.debug("Hardware monitor sensor lookup failed: %s", exc)
    return None


def libre_hardware_monitor_library_temperature(label: str) -> float | None:
    if label.lower() == "cpu":
        return libre_hardware_monitor_library_sensor_value("Temperature", ["cpu", "core", "package", "tctl", "tdie"], ["distance", "tjmax"])
    if label.lower() == "disk":
        return libre_hardware_monitor_library_sensor_value("Temperature", ["hdd", "ssd", "nvme", "drive", "disk"], [])
    return None


def libre_hardware_monitor_library_sensor_value(
    sensor_type: str,
    keywords: list[str],
    exclude_keywords: list[str],
    require_all_keywords: bool = False,
) -> float | None:
    if os.name != "nt":
        return None
    dll_path = LHM_DLL_PATH
    if not dll_path.is_absolute():
        dll_path = (Path(__file__).resolve().parent / dll_path).resolve()
    if not dll_path.exists():
        return None
    keywords_ps = powershell_string_array([keyword.lower() for keyword in keywords])
    excludes_ps = powershell_string_array([keyword.lower() for keyword in exclude_keywords])
    require_all = "$true" if require_all_keywords else "$false"
    normalized_type = sensor_type
    script = f"""
Add-Type -Path '{str(dll_path).replace("'", "''")}'
$computer = [LibreHardwareMonitor.Hardware.Computer]::new()
$computer.IsCpuEnabled = $true
$computer.IsStorageEnabled = $true
$computer.IsMotherboardEnabled = $true
$computer.IsGpuEnabled = $true
$computer.IsMemoryEnabled = $true
$computer.Open()
Start-Sleep -Milliseconds 600
$keywords = {keywords_ps}
$excludes = {excludes_ps}
$requireAll = {require_all}
$script:values = @()
$script:namedValues = @()
function Read-Hardware($hardware) {{
  $hardware.Update()
  foreach ($subHardware in $hardware.SubHardware) {{ Read-Hardware $subHardware }}
  foreach ($sensor in $hardware.Sensors) {{
    if ($sensor.SensorType.ToString() -ne '{normalized_type}' -or $null -eq $sensor.Value) {{ continue }}
    $text = ($sensor.Name + ' ' + $hardware.Name + ' ' + $hardware.HardwareType.ToString() + ' ' + $sensor.Identifier.ToString()).ToLowerInvariant()
    $excluded = $false
    foreach ($exclude in $excludes) {{
      if ($text.Contains($exclude)) {{ $excluded = $true }}
    }}
    if ($excluded) {{ continue }}
    $matched = $true
    if ($keywords.Count -gt 0) {{
      $matched = $requireAll
      foreach ($keyword in $keywords) {{
        if ($requireAll -and -not $text.Contains($keyword)) {{ $matched = $false }}
        if (-not $requireAll -and $text.Contains($keyword)) {{ $matched = $true }}
      }}
    }}
    if ($matched) {{
      $script:values += [double]$sensor.Value
      $script:namedValues += [pscustomobject]@{{ Text = $text; Value = [double]$sensor.Value }}
    }}
  }}
}}
foreach ($hardware in $computer.Hardware) {{ Read-Hardware $hardware }}
$computer.Close()
if ('{normalized_type}' -eq 'Temperature' -and $script:namedValues.Count -gt 0) {{
  $preferred = $script:namedValues | Where-Object {{ $_.Text -match 'package|tctl|tdie|cpu die|ccd' }} | Sort-Object Value -Descending | Select-Object -First 1
  if ($preferred) {{ [Math]::Round($preferred.Value, 2); exit }}
  [Math]::Round(($script:namedValues | Measure-Object -Property Value -Maximum).Maximum, 2)
  exit
}}
if ($script:values.Count -gt 0) {{ [Math]::Round(($script:values | Measure-Object -Average).Average, 2) }}
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            text=True,
            capture_output=True,
            timeout=12,
            check=False,
        )
        output = result.stdout.strip().splitlines()
        if output:
            return float(output[-1])
    except Exception as exc:
        logger.debug("LibreHardwareMonitor library lookup failed: %s", exc)
    return None


def select_temperature_value(label: str, values: list[tuple[str, float]]) -> float | None:
    if not values:
        return None
    sane_values = [(text, value) for text, value in values if 0 < value < 125]
    if not sane_values:
        return None
    if label == "cpu":
        preferred = [
            (text, value)
            for text, value in sane_values
            if any(keyword in text for keyword in ("package", "tctl", "tdie", "cpu die", "ccd"))
        ]
        if preferred:
            return round(max(value for _, value in preferred), 2)
        return round(max(value for _, value in sane_values), 2)
    return round(sum(value for _, value in sane_values) / len(sane_values), 2)


def nvidia_smi_fan_speed_percent() -> float | None:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=fan.speed",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except Exception as exc:
        logger.debug("nvidia-smi lookup failed: %s", exc)
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None

    fan_speed_percent = []
    for line in result.stdout.splitlines():
        try:
            fan_speed_percent.append(float(line.strip()))
        except ValueError:
            pass

    return round(sum(fan_speed_percent) / len(fan_speed_percent), 2) if fan_speed_percent else None


def powershell_string_array(values: list[str]) -> str:
    if not values:
        return "@()"
    escaped = [f"'{value.replace(chr(39), chr(39) + chr(39))}'" for value in values]
    return "@(" + ", ".join(escaped) + ")"


def wmi_thermal_zone_temperature() -> float | None:
    if not wmi:
        return None
    try:
        thermal = wmi.WMI(namespace="root\\wmi").MSAcpi_ThermalZoneTemperature()
        values = []
        for zone in thermal:
            raw = getattr(zone, "CurrentTemperature", None)
            if raw:
                celsius = (float(raw) / 10.0) - 273.15
                if 0 < celsius < 125:
                    values.append(celsius)
        if values:
            return round(sum(values) / len(values), 2)
    except Exception as exc:
        logger.debug("WMI thermal zone lookup failed: %s", exc)
    return None


def disk_smart_health() -> str | None:
    if os.name != "nt":
        return None
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-PhysicalDisk | Select-Object -First 1 -ExpandProperty HealthStatus"],
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
        value = result.stdout.strip().lower()
        if value:
            return "ok" if value == "healthy" else value
    except Exception as exc:
        logger.debug("SMART health lookup failed: %s", exc)
    return None


def ping_stats() -> tuple[float | None, float | None]:
    try:
        result = subprocess.run(["ping", "-n", "4", "8.8.8.8"], text=True, capture_output=True, timeout=10, check=False)
        output = result.stdout
        loss = latency = None
        for line in output.splitlines():
            if "Lost =" in line and "(" in line:
                loss = float(line.split("(")[1].split("%")[0])
            if "Average =" in line:
                latency = float(line.split("Average =")[1].replace("ms", "").strip())
        return latency, loss
    except Exception as exc:
        logger.debug("Ping failed: %s", exc)
        return None, None


def battery_stats() -> tuple[float | None, bool | None, float | None]:
    battery = psutil.sensors_battery()
    percentage = battery.percent if battery else None
    charging = battery.power_plugged if battery else None
    health = None
    if wmi:
        try:
            batteries = wmi.WMI(namespace="root\\wmi").BatteryFullChargedCapacity()
            designed = wmi.WMI(namespace="root\\wmi").BatteryStaticData()
            if batteries and designed and designed[0].DesignedCapacity:
                health = min(100.0, (float(batteries[0].FullChargedCapacity) / float(designed[0].DesignedCapacity)) * 100)
        except Exception as exc:
            logger.debug("Battery health lookup failed: %s", exc)
    return percentage, charging, health


def collect_reading(device_id: str) -> dict[str, Any]:
    disk = psutil.disk_usage(os.getenv("SYSTEMDRIVE", "C:") + "\\")
    latency, loss = ping_stats()
    battery_percentage, _, battery_health = battery_stats()
    cpu_temperature = safe_temperature("cpu")
    disk_temperature = safe_temperature("disk")
    fan_speed_rpm = safe_fan_speed_rpm()
    fan_speed_percent = safe_fan_speed_percent()
    return {
        "device_id": device_id,
        "cpu_usage": psutil.cpu_percent(interval=1),
        "cpu_temperature": cpu_temperature,
        "fan_speed_rpm": fan_speed_rpm,
        "fan_speed_percent": fan_speed_percent,
        "ram_usage": psutil.virtual_memory().percent,
        "disk_usage": disk.percent,
        "disk_temperature": disk_temperature,
        "disk_health": disk_smart_health(),
        "battery_percentage": battery_percentage,
        "battery_health": battery_health,
        "network_latency": latency,
        "packet_loss": loss,
        "uptime_seconds": int(time.time() - psutil.boot_time()),
        "recorded_at": utc_now(),
    }


def collect_events(device_id: str) -> list[dict[str, Any]]:
    if os.name != "nt":
        return []
    command = (
        "Get-WinEvent -FilterHashtable @{LogName='System'; Level=1,2; StartTime=(Get-Date).AddMinutes(-5)} "
        "-MaxEvents 20 | Select-Object ProviderName,LevelDisplayName,Message,TimeCreated | ConvertTo-Json -Depth 3"
    )
    try:
        result = subprocess.run(["powershell", "-NoProfile", "-Command", command], text=True, capture_output=True, timeout=10, check=False)
        if not result.stdout.strip():
            return []
        parsed = json.loads(result.stdout)
        rows = parsed if isinstance(parsed, list) else [parsed]
        return [
            {
                "device_id": device_id,
                "event_type": "windows_event",
                "severity": "critical" if row.get("LevelDisplayName") == "Critical" else "error",
                "source": row.get("ProviderName"),
                "message": (row.get("Message") or "")[:2000],
                "occurred_at": row.get("TimeCreated") or utc_now(),
            }
            for row in rows
            if row.get("Message")
        ]
    except Exception as exc:
        logger.debug("Event collection failed: %s", exc)
        return []


class Queue:
    def __init__(self, path: Path) -> None:
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            "create table if not exists outbound (id integer primary key autoincrement, endpoint text not null, payload text not null, created_at text not null)"
        )
        self.conn.commit()

    def add(self, endpoint: str, payload: dict[str, Any]) -> None:
        self.conn.execute("insert into outbound(endpoint,payload,created_at) values(?,?,?)", (endpoint, json.dumps(payload), utc_now()))
        self.conn.commit()

    def drain(self, post_func) -> None:
        rows = self.conn.execute("select id, endpoint, payload from outbound order by id limit 50").fetchall()
        for row_id, endpoint, payload in rows:
            if post_func(endpoint, json.loads(payload)):
                self.conn.execute("delete from outbound where id = ?", (row_id,))
                self.conn.commit()
            else:
                break


def post(endpoint: str, payload: dict[str, Any]) -> bool:
    url = f"{API_BASE_URL}/api/{endpoint}"
    try:
        response = requests.post(url, headers={"X-Agent-Api-Key": AGENT_API_KEY}, json=payload, timeout=10)
        if response.status_code >= 500:
            logger.warning("Post failed server=%s endpoint=%s status=%s body=%s", API_BASE_URL, url, response.status_code, response.text[:500])
            return False
        response.raise_for_status()
        return True
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        body = exc.response.text[:500] if exc.response is not None else ""
        logger.warning("Post failed server=%s endpoint=%s status=%s error=%s body=%s", API_BASE_URL, url, status_code, exc, body)
        return False
    except Exception as exc:
        logger.warning("Post failed server=%s endpoint=%s error=%s", API_BASE_URL, url, exc)
        return False


def agent_headers() -> dict[str, str]:
    return {"X-Agent-Api-Key": AGENT_API_KEY}


def run_limited_command(args: list[str], timeout: int = 20) -> dict[str, Any]:
    result = subprocess.run(args, text=True, capture_output=True, timeout=timeout, check=False)
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout[-12000:],
        "stderr": result.stderr[-4000:],
    }


def powershell_json(command: str, timeout: int = 20) -> dict[str, Any]:
    return run_limited_command(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command], timeout)


def schedule_self_uninstall() -> dict[str, Any]:
    if os.name != "nt":
        return {"message": "Uninstall is only supported on Windows agents."}
    task_name = "PC Sentinel Agent"
    startup_dir = Path(os.getenv("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    launcher = startup_dir / "pc-sentinel-agent.cmd"
    cleanup = AGENT_DIR / "pc-sentinel-uninstall.cmd"
    script = f"""@echo off
timeout /t 5 /nobreak >nul
schtasks /Delete /TN "{task_name}" /F >nul 2>nul
del "{launcher}" >nul 2>nul
rmdir /s /q "{AGENT_DIR}" >nul 2>nul
"""
    cleanup.write_text(script, encoding="ascii")
    subprocess.Popen(["cmd", "/c", "start", "", "/min", str(cleanup)], cwd=str(AGENT_DIR), shell=False)
    return {"message": "Agent uninstall scheduled."}


def execute_agent_command(action: str) -> dict[str, Any]:
    if action == "system_info":
        return {
            "computer": computer_metadata(),
            "boot_time": datetime.fromtimestamp(psutil.boot_time(), timezone.utc).isoformat(),
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        }
    if action == "process_list":
        processes = []
        for proc in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent"]):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return {"processes": sorted(processes, key=lambda item: item.get("memory_percent") or 0, reverse=True)[:40]}
    if action == "services_list":
        if os.name != "nt":
            return {"services": []}
        return powershell_json("Get-Service | Select-Object -First 80 Name,DisplayName,Status | ConvertTo-Json -Depth 3")
    if action == "disk_summary":
        disks = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except OSError:
                continue
            disks.append({"device": part.device, "mountpoint": part.mountpoint, "fstype": part.fstype, "percent": usage.percent, "free_gb": round(usage.free / (1024**3), 2)})
        return {"disks": disks}
    if action == "network_test":
        latency, loss = ping_stats()
        return {"target": "8.8.8.8", "latency_ms": latency, "packet_loss_percent": loss}
    if action == "restart":
        if os.name == "nt":
            subprocess.Popen(["shutdown", "/r", "/t", "60", "/c", "PC Sentinel administrator requested restart"], shell=False)
            return {"message": "Restart scheduled in 60 seconds."}
        return {"message": "Restart is only supported on Windows agents."}
    if action == "shutdown":
        if os.name == "nt":
            subprocess.Popen(["shutdown", "/s", "/t", "60", "/c", "PC Sentinel administrator requested shutdown"], shell=False)
            return {"message": "Shutdown scheduled in 60 seconds."}
        return {"message": "Shutdown is only supported on Windows agents."}
    if action == "uninstall_agent":
        return schedule_self_uninstall()
    raise ValueError(f"Unsupported command action: {action}")


def poll_agent_commands(device_id: str) -> None:
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/agents/commands/pending",
            headers=agent_headers(),
            params={"device_id": device_id},
            timeout=10,
        )
        if response.status_code == 404:
            return
        response.raise_for_status()
        commands = response.json().get("items", [])
    except Exception as exc:
        logger.debug("Command polling failed: %s", exc)
        return

    for command in commands:
        command_id = command.get("id")
        action = command.get("action")
        status = "completed"
        result: dict[str, Any] | None = None
        error: str | None = None
        try:
            result = execute_agent_command(action)
        except Exception as exc:
            status = "failed"
            error = str(exc)
            logger.warning("Command %s failed: %s", action, exc)
        try:
            requests.post(
                f"{API_BASE_URL}/api/agents/commands/{command_id}/complete",
                headers=agent_headers(),
                json={"status": status, "result": result or {}, "error": error},
                timeout=10,
            ).raise_for_status()
        except Exception as exc:
            logger.warning("Command completion post failed for %s: %s", command_id, exc)


def request_stop(*_: Any) -> None:
    global stop_requested
    stop_requested = True


def check_in_once() -> int:
    log_startup_context()
    if not AGENT_API_KEY:
        logger.error("AGENT_API_KEY is required")
        print("AGENT_API_KEY is required")
        return 1

    if not check_api_health():
        print(f"Could not reach {API_BASE_URL}. Check agent.log for details.")
        return 1

    metadata = computer_metadata()
    if post("agents/register", metadata):
        reading = collect_reading(metadata["device_id"])
        if post("readings", reading):
            print(f"Registered {metadata['computer_name']} with PC Sentinel and uploaded first diagnostics reading.")
            return 0
        print(f"Registered {metadata['computer_name']}, but could not upload diagnostics data. Check agent.log for details.")
        return 1

    print(f"Could not register with {API_BASE_URL}. Check agent.log for details.")
    return 1


def main() -> None:
    log_startup_context()
    if not AGENT_API_KEY:
        raise RuntimeError("AGENT_API_KEY is required")
    check_api_health()
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    queue = Queue(QUEUE_PATH)
    metadata = computer_metadata()
    backoff = 1
    while not stop_requested:
        poll_agent_commands(metadata["device_id"])
        if not post("agents/register", metadata):
            queue.add("agents/register", metadata)
        reading = collect_reading(metadata["device_id"])
        if not post("readings", reading):
            queue.add("readings", reading)
            backoff = min(backoff * 2, 60)
        else:
            backoff = 1
        for event in collect_events(metadata["device_id"]):
            if not post("events", event):
                queue.add("events", event)
        queue.drain(post)
        time.sleep(max(INTERVAL, backoff))


if __name__ == "__main__":
    if ARGS.once:
        raise SystemExit(check_in_once())
    main()
