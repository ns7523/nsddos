"""UI app factory."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from nsddos.api.middleware import install_middleware
from nsddos.api.router import router as api_router
from nsddos.ui.router import PRIMARY_PATHS, EXPLORER_PATHS, builder, render_page, router as ui_router
from nsddos.ui.state import build_ui_state

STATIC_DIR = Path(__file__).with_name("static")
FAVICON_PATH = STATIC_DIR / "brand" / "favicon.svg"


def create_ui_app() -> FastAPI:
    app = FastAPI(
        title="NS-DDoS Operational Observability UI",
        version="0.1.0",
        description="Enterprise runtime observability interface",
    )
    install_middleware(app)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def ui_root(request: Request):
        return render_page(request, builder.overview(), landing=True)

    @app.get("/dashboard", include_in_schema=False)
    def ui_dashboard_redirect() -> RedirectResponse:
        return RedirectResponse(url="/ui", status_code=307)

    @app.get("/ui/healthz", include_in_schema=False)
    def ui_healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/favicon.ico", include_in_schema=False)
    def ui_favicon() -> FileResponse:
        return FileResponse(FAVICON_PATH, media_type="image/svg+xml")

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
        "surfaces": [*PRIMARY_PATHS, *EXPLORER_PATHS],
        "state": state.to_dict(),
    }


app = create_ui_app()
