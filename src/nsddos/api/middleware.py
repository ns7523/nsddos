"""API middleware."""

from __future__ import annotations

from time import monotonic

from fastapi import FastAPI, Request

from nsddos.runtime.performance import record_timing


def install_middleware(app: FastAPI) -> None:
    """Install deterministic request timing middleware."""

    @app.middleware("http")
    async def request_timing(request: Request, call_next):
        start = monotonic()
        response = await call_next(request)
        duration_ms = (monotonic() - start) * 1000
        response.headers["X-NSDDOS-Request-Time-Ms"] = f"{duration_ms:.2f}"
        record_timing("api_request", duration_ms)
        return response
