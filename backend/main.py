import logging
import asyncio
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import get_settings
from middleware.errors import install_error_handlers
from middleware.rate_limit import agent_rate_limit
from routers import agents, alerts, audit, computers, dashboard, diagnostics, health, ingestion, installer, maintenance, organization, reports, settings, tickets, users

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app_settings = get_settings()


async def _offline_sweep() -> None:
    from database import get_supabase_admin
    from services.offline import mark_stale_computers
    while True:
        try:
            await asyncio.to_thread(mark_stale_computers, get_supabase_admin())
        except Exception:
            logging.getLogger("pc_sentinel.offline").exception("Offline sweep failed")
        await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(_offline_sweep())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Computer Diagnostic API", version="0.1.0", lifespan=lifespan)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "computer-monitoring-api",
        "status": "ok",
        "health": "/api/health",
        "docs": "/docs",
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Agent-Api-Key"],
)
install_error_handlers(app)
app.middleware("http")(agent_rate_limit)

app.include_router(health.router, prefix="/api")
app.include_router(agents.router, prefix="/api/agents")
# The existing plural routes remain supported; the singular path is the
# documented Windows-agent contract and points at the same handlers.
app.include_router(agents.router, prefix="/api/agent")
app.include_router(ingestion.router, prefix="/api")
app.include_router(installer.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(computers.router, prefix="/api/computers")
app.include_router(computers.router, prefix="/api/devices")
app.include_router(diagnostics.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(tickets.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(maintenance.router, prefix="/api")
app.include_router(organization.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
