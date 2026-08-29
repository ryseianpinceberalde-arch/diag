from collections import defaultdict, deque
from time import monotonic
from fastapi import Request
from fastapi.responses import JSONResponse

WINDOW_SECONDS = 60
MAX_AGENT_REQUESTS = 240
requests_by_key: dict[str, deque[float]] = defaultdict(deque)


async def agent_rate_limit(request: Request, call_next):
    if request.url.path in {
        "/api/agents/register", "/api/agents/heartbeat", "/api/agents/telemetry",
        "/api/agent/register", "/api/agent/heartbeat", "/api/agent/telemetry",
        "/api/readings", "/api/events",
    }:
        key = request.headers.get("x-agent-api-key") or request.client.host if request.client else "unknown"
        now = monotonic()
        bucket = requests_by_key[key]
        while bucket and now - bucket[0] > WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= MAX_AGENT_REQUESTS:
            return JSONResponse(status_code=429, content={"detail": "Too many ingestion requests"})
        bucket.append(now)
    return await call_next(request)
