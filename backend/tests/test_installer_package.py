from zipfile import ZipFile

from routers.installer import build_agent_package


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
