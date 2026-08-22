import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import get_settings
from middleware.errors import install_error_handlers
from middleware.rate_limit import agent_rate_limit
from routers import agents, alerts, computers, dashboard, health, ingestion, installer, reports

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

settings = get_settings()
app = FastAPI(title="Computer Diagnostic API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Agent-Api-Key"],
)
install_error_handlers(app)
app.middleware("http")(agent_rate_limit)

app.include_router(health.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(ingestion.router, prefix="/api")
app.include_router(installer.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(computers.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
