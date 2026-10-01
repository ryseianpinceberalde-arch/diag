from zipfile import ZipFile

from fastapi import Request
from config import Settings
from routers.installer import build_agent_package, install_script


def test_agent_package_does_not_ship_localhost_api_url():
    package = build_agent_package()
    forbidden = ("http://localhost:8000", "localhost:8000", "127.0.0.1:8000")

    with ZipFile(package) as archive:
        for name in archive.namelist():
            if not name.endswith((".py", ".ps1", ".txt", ".env", ".example")):
                continue
            content = archive.read(name).decode("utf-8", errors="ignore")
            for value in forbidden:
                assert value not in content, f"{value} found in packaged {name}"


def test_generated_installer_uses_user_run_key_when_scheduled_task_is_denied():
    settings = Settings(
        _env_file=None,
        SUPABASE_URL="https://example.supabase.co",
        SUPABASE_ANON_KEY="test-anon",
        SUPABASE_SERVICE_ROLE_KEY="test-service",
        AGENT_API_KEY="test-agent-key",
    )
    request = Request({
        "type": "http", "method": "GET", "scheme": "https",
        "server": ("api.example.test", 443), "path": "/api/installer/install.ps1",
        "query_string": b"", "headers": [],
    })
    script = install_script(request, token=None, settings=settings).body.decode()
    assert 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run' in script
    assert 'New-ItemProperty -LiteralPath $runKey -Name "PC Sentinel Agent"' in script
    assert "[Environment]::GetFolderPath(\"Startup\")" not in script
    assert "Set-Content -Encoding ASCII -Path $cmdPath" not in script
