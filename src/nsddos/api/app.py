"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from nsddos.api.middleware import install_middleware
from nsddos.api.router import route_summary, router


def create_app() -> FastAPI:
    """Create read-only NS-DDoS runtime API."""
    app = FastAPI(
        title="NS-DDoS Runtime API",
        version="0.1.0",
        description="Read-only query-backed runtime API.",
    )
    install_middleware(app)
    app.include_router(router)
    return app


def get_route_summary() -> dict:
    """Return route summary for CLI/verification."""
    return route_summary(create_app().routes).model_dump()


def explain_api() -> dict:
    """Explain API architecture."""
    return {
        "readonly": True,
        "query_backed": True,
        "provider_access": "forbidden",
        "orchestration_access": "forbidden",
        "route_summary": get_route_summary(),
        "principles": [
            "API consumes runtime query engine",
            "API consumes verification explainability",
            "API responses include schema_version and evidence refs",
            "API does not mutate runtime state",
        ],
    }


app = create_app()
