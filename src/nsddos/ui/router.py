"""UI router."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from nsddos.ui.api_client import UiApiClient
from nsddos.ui.dashboard_pages import EXPLORER_PATHS, PRIMARY_PATHS, UiPageBuilder
from nsddos.ui.lab_console import control_manager, stream_terminal, terminal_manager
from nsddos.ui.models import UiNavItem, UiPagePayload

router = APIRouter(prefix="/ui", tags=["ui"])
client = UiApiClient()
builder = UiPageBuilder(client)
templates = Jinja2Templates(directory=str(Path(__file__).with_name("templates")))


def build_navigation(active_path: str) -> tuple[UiNavItem, ...]:
    primary = (
        ("OVERVIEW", "/ui", "Primary", ""),
        ("LIVE TOPOLOGY", "/ui/infrastructure", "Primary", ""),
        ("DETECTION ENGINE", "/ui/detection", "Primary", ""),
        ("MITIGATION PANEL", "/ui/mitigation", "Primary", ""),
        ("LIVE TRAFFIC", "/ui/live-traffic", "Primary", ""),
        ("ATTACK SIMULATOR", "/ui/attack-logs", "Primary", ""),
        ("DOCTOR PANEL", "/ui/doctor", "Primary", ""),
        ("SESSION PANEL", "/ui/session", "Primary", ""),
    )
    explorer = (
        ("LAB CONSOLE", "/ui/lab-console", "Explorer", ""),
        ("VERIFICATION", "/ui/verification", "Explorer", ""),
        ("CONVERGENCE", "/ui/convergence", "Explorer", ""),
        ("GRAPH", "/ui/graph", "Explorer", ""),
        ("TIMELINE", "/ui/timeline", "Explorer", ""),
        ("EVIDENCE", "/ui/evidence", "Explorer", ""),
        ("REPLAY", "/ui/replay", "Explorer", ""),
        ("SESSIONS", "/ui/sessions", "Explorer", ""),
        ("SERVICE", "/ui/service", "Explorer", ""),
        ("DIAGNOSTICS", "/ui/diagnostics", "Explorer", ""),
        ("DRIFT", "/ui/drift", "Explorer", ""),
        ("SYNCHRONIZATION", "/ui/synchronization", "Explorer", ""),
    )
    return tuple(
        UiNavItem(
            label=label, path=path, group=group, icon=icon, active=active_path == path
        )
        for label, path, group, icon in (*primary, *explorer)
    )


def render_page(
    request: Request, page: UiPagePayload, *, landing: bool = False
) -> HTMLResponse:
    del landing
    ws_path = f"/ui/ws/{page.name}" if page.active_path in PRIMARY_PATHS else ""
    template_name = "lab_console.html" if page.lab_console is not None else "page.html"
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context={
            "request": request,
            "page": page,
            "page_json": page.to_dict(),
            "nav_items": build_navigation(page.active_path),
            "ws_path": ws_path,
            "primary_paths": PRIMARY_PATHS,
            "explorer_paths": EXPLORER_PATHS,
        },
    )


def _payload(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    return client.get(path, params=params or {})


@router.get("", response_class=HTMLResponse)
def ui_overview(request: Request) -> HTMLResponse:
    return render_page(request, builder.overview())


@router.get("/lab-console", response_class=HTMLResponse)
def ui_lab_console(request: Request) -> HTMLResponse:
    return render_page(request, builder.lab_console())


@router.get("/infrastructure", response_class=HTMLResponse)
def ui_infrastructure(request: Request) -> HTMLResponse:
    return render_page(request, builder.infrastructure())


@router.get("/detection", response_class=HTMLResponse)
def ui_detection(request: Request) -> HTMLResponse:
    return render_page(request, builder.detection())


@router.get("/mitigation", response_class=HTMLResponse)
def ui_mitigation(request: Request) -> HTMLResponse:
    return render_page(request, builder.mitigation())


@router.get("/live-traffic", response_class=HTMLResponse)
def ui_live_traffic(request: Request) -> HTMLResponse:
    return render_page(request, builder.live_traffic())


@router.get("/attack-logs", response_class=HTMLResponse)
def ui_attack_logs(request: Request) -> HTMLResponse:
    return render_page(request, builder.attack_logs())


@router.get("/doctor", response_class=HTMLResponse)
def ui_doctor(request: Request) -> HTMLResponse:
    return render_page(request, builder.doctor())


@router.get("/session", response_class=HTMLResponse)
def ui_session(request: Request) -> HTMLResponse:
    return render_page(request, builder.session())


@router.get("/verification", response_class=HTMLResponse)
def ui_verification(
    request: Request,
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> HTMLResponse:
    return render_page(
        request,
        builder.explorer(
            "/ui/verification",
            "Verification",
            "/runtime/verification",
            "verification rules and evidence",
            {"limit": limit, "offset": offset},
        ),
    )


@router.get("/convergence", response_class=HTMLResponse)
def ui_convergence(
    request: Request,
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> HTMLResponse:
    return render_page(
        request,
        builder.explorer(
            "/ui/convergence",
            "Convergence",
            "/runtime/convergence",
            "convergence snapshots",
            {"limit": limit, "offset": offset},
        ),
    )


@router.get("/graph", response_class=HTMLResponse)
def ui_graph(
    request: Request,
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> HTMLResponse:
    return render_page(
        request,
        builder.explorer(
            "/ui/graph",
            "Graph",
            "/runtime/graph",
            "runtime graph entities",
            {"limit": limit, "offset": offset},
        ),
    )


@router.get("/timeline", response_class=HTMLResponse)
def ui_timeline(
    request: Request,
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> HTMLResponse:
    return render_page(
        request,
        builder.explorer(
            "/ui/timeline",
            "Timeline",
            "/runtime/timeline",
            "time-ordered runtime events",
            {"limit": limit, "offset": offset},
        ),
    )


@router.get("/evidence", response_class=HTMLResponse)
def ui_evidence(
    request: Request,
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> HTMLResponse:
    return render_page(
        request,
        builder.explorer(
            "/ui/evidence",
            "Evidence",
            "/runtime/evidence",
            "evidence bundles",
            {"limit": limit, "offset": offset},
        ),
    )


@router.get("/replay", response_class=HTMLResponse)
def ui_replay(
    request: Request,
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> HTMLResponse:
    return render_page(
        request,
        builder.explorer(
            "/ui/replay",
            "Replay",
            "/runtime/replay",
            "replay-safe history",
            {"limit": limit, "offset": offset},
        ),
    )


@router.get("/sessions", response_class=HTMLResponse)
def ui_sessions(
    request: Request,
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> HTMLResponse:
    return render_page(
        request,
        builder.explorer(
            "/ui/sessions",
            "Sessions",
            "/runtime/service",
            "runtime sessions",
            {"limit": limit, "offset": offset},
        ),
    )


@router.get("/service", response_class=HTMLResponse)
def ui_service(
    request: Request,
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> HTMLResponse:
    return render_page(
        request,
        builder.explorer(
            "/ui/service",
            "Service",
            "/runtime/service",
            "service ownership and state",
            {"limit": limit, "offset": offset},
        ),
    )


@router.get("/diagnostics", response_class=HTMLResponse)
def ui_diagnostics(
    request: Request,
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> HTMLResponse:
    return render_page(
        request,
        builder.explorer(
            "/ui/diagnostics",
            "Diagnostics",
            "/runtime/service",
            "service diagnostics",
            {"limit": limit, "offset": offset},
        ),
    )


@router.get("/drift", response_class=HTMLResponse)
def ui_drift(
    request: Request,
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> HTMLResponse:
    return render_page(
        request,
        builder.explorer(
            "/ui/drift",
            "Drift",
            "/runtime/drift",
            "temporal drift analysis",
            {"limit": limit, "offset": offset},
        ),
    )


@router.get("/synchronization", response_class=HTMLResponse)
def ui_synchronization(
    request: Request,
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> HTMLResponse:
    return render_page(
        request,
        builder.explorer(
            "/ui/synchronization",
            "Synchronization",
            "/runtime/service",
            "runtime synchronization state",
            {"limit": limit, "offset": offset},
        ),
    )


@router.post("/api/lab/actions/{action}")
def ui_lab_action(action: str) -> JSONResponse:
    return JSONResponse(control_manager.run_action(action))


async def _stream_snapshot(websocket: WebSocket, name: str) -> None:
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(builder.snapshot_for(name).to_dict())
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return


@router.websocket("/ws/overview")
async def ws_overview(websocket: WebSocket) -> None:
    await _stream_snapshot(websocket, "overview")


@router.websocket("/ws/lab-console")
async def ws_lab_console(websocket: WebSocket) -> None:
    await _stream_snapshot(websocket, "lab-console")


@router.websocket("/ws/lab-terminal/{host}")
async def ws_lab_terminal(websocket: WebSocket, host: str) -> None:
    await stream_terminal(websocket, host, terminal_manager)


@router.websocket("/ws/infrastructure")
async def ws_infrastructure(websocket: WebSocket) -> None:
    await _stream_snapshot(websocket, "infrastructure")


@router.websocket("/ws/detection")
async def ws_detection(websocket: WebSocket) -> None:
    await _stream_snapshot(websocket, "detection")


@router.websocket("/ws/mitigation")
async def ws_mitigation(websocket: WebSocket) -> None:
    await _stream_snapshot(websocket, "mitigation")


@router.websocket("/ws/live-traffic")
async def ws_live_traffic(websocket: WebSocket) -> None:
    await _stream_snapshot(websocket, "live-traffic")


@router.websocket("/ws/attack-logs")
async def ws_attack_logs(websocket: WebSocket) -> None:
    await _stream_snapshot(websocket, "attack-logs")


@router.websocket("/ws/doctor")
async def ws_doctor(websocket: WebSocket) -> None:
    await _stream_snapshot(websocket, "doctor")


@router.websocket("/ws/session")
async def ws_session(websocket: WebSocket) -> None:
    await _stream_snapshot(websocket, "session")
