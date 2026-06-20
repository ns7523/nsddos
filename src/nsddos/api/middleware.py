"""API middleware."""

from __future__ import annotations

import os
import secrets
from time import monotonic

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from nsddos.runtime.performance import record_timing

PUBLIC_PATHS = {
    "/health",
    "/docs",
    "/docs/oauth2-redirect",
    "/openapi.json",
    "/redoc",
    "/favicon.ico",
}


def _authorized(request: Request) -> bool:
    token = os.getenv("NSDDOS_API_TOKEN", "").strip()
    if not token or request.url.path in PUBLIC_PATHS:
        return True
    bearer = request.headers.get("authorization", "").strip()
    supplied = request.headers.get("x-nsddos-api-token", "").strip()
    if bearer.lower().startswith("bearer "):
        supplied = bearer[7:].strip()
    return bool(supplied) and secrets.compare_digest(supplied, token)


def install_middleware(app: FastAPI) -> None:
    """Install deterministic request timing middleware."""

    @app.middleware("http")
    async def request_timing(request: Request, call_next):
        if not _authorized(request):
            return JSONResponse(status_code=401, content={"detail": "missing or invalid api token"})
        start = monotonic()
        response = await call_next(request)
        duration_ms = (monotonic() - start) * 1000
        response.headers["X-NSDDOS-Request-Time-Ms"] = f"{duration_ms:.2f}"
        record_timing("api_request", duration_ms)
        return response
