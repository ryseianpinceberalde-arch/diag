import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from config import get_settings

logger = logging.getLogger("diagnostic")


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled backend error: %s", exc)
        headers: dict[str, str] = {}
        origin = request.headers.get("origin")
        if origin and origin in get_settings().cors_origins:
            headers = {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
                "Vary": "Origin",
            }
        return JSONResponse(status_code=500, content={"detail": "Internal server error"}, headers=headers)
