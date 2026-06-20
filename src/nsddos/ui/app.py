"""UI app factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from nsddos.api.router import router as api_router
from nsddos.api.middleware import install_middleware
from nsddos.ui.components.layout import page_layout
from nsddos.ui.router import router as ui_router
from nsddos.ui.components.navigation import render_navigation
from nsddos.ui.components.status_bar import render_status_bar
from nsddos.ui.state import build_ui_state


def create_ui_app() -> FastAPI:
    app = FastAPI(
        title="NS-DDoS Operational Observability UI",
        version="0.1.0",
        description="Deterministic runtime observability interface",
    )
    install_middleware(app)

    @app.get("/", response_class=HTMLResponse)
    def ui_root() -> HTMLResponse:
        body = (
            "<h1>NSDDOS Control Panel</h1>"
            "<p>Operational entry surface for runtime UI and API checks.</p>"
            "<ul>"
            "<li><a href='/dashboard'>Dashboard</a></li>"
            "<li><a href='/health'>Health</a></li>"
            "<li><a href='/runtime/service'>Runtime Status</a></li>"
            "<li><a href='/runtime/detection'>Detection</a></li>"
            "<li><a href='/runtime/mitigation'>Mitigation</a></li>"
            "<li><a href='/docs'>API Docs</a></li>"
            "</ul>"
        )
        return HTMLResponse(
            page_layout(
                "NSDDOS Control Panel",
                render_navigation(),
                render_status_bar(
                    {
                        "readonly": True,
                        "query_backed": True,
                        "entrypoint": "/",
                    }
                ),
                body,
            )
        )

    @app.get("/dashboard", include_in_schema=False)
    def ui_dashboard_redirect() -> RedirectResponse:
        return RedirectResponse(url="/ui", status_code=307)

    @app.get("/favicon.ico", include_in_schema=False)
    def ui_favicon() -> Response:
        return Response(content=b"", media_type="image/x-icon")

    app.include_router(ui_router)
    app.include_router(api_router)
    return app


def explain_ui() -> dict:
    state = build_ui_state()
    return {
        "readonly": True,
        "query_backed": True,
        "api_only": True,
        "replay_safe": True,
        "surfaces": [
            "overview",
            "verification",
            "convergence",
            "graph",
            "timeline",
            "evidence",
            "replay",
            "sessions",
            "service",
            "diagnostics",
            "drift",
            "synchronization",
        ],
        "state": state.to_dict(),
    }


app = create_ui_app()
