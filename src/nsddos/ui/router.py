"""UI router."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from nsddos.ui.api_client import UiApiClient
from nsddos.ui.components.convergence_view import render_convergence_view
from nsddos.ui.components.diagnostics_view import render_diagnostics_view
from nsddos.ui.components.evidence_view import render_evidence_view
from nsddos.ui.components.graph_view import render_graph_view
from nsddos.ui.components.layout import page_layout
from nsddos.ui.components.navigation import render_navigation
from nsddos.ui.components.replay_view import render_replay_view
from nsddos.ui.components.session_view import render_session_view
from nsddos.ui.components.status_bar import render_status_bar
from nsddos.ui.components.tables import render_items_table
from nsddos.ui.components.timeline_view import render_timeline_view
from nsddos.ui.components.verification_view import render_verification_view
from nsddos.ui.convergence import build_convergence_payload
from nsddos.ui.diagnostics import build_diagnostics_payload
from nsddos.ui.evidence import build_evidence_payload
from nsddos.ui.graph import build_graph_payload
from nsddos.ui.replay import build_replay_payload
from nsddos.ui.sessions import build_sessions_payload
from nsddos.ui.synchronization import deterministic_poll
from nsddos.ui.timeline import build_timeline_payload
from nsddos.ui.verification import build_verification_payload

router = APIRouter(prefix="/ui", tags=["ui"])
client = UiApiClient()


def _wrap(title: str, body: str, summary: dict[str, Any]) -> HTMLResponse:
    return HTMLResponse(page_layout(title, render_navigation(), render_status_bar(summary), body))


def _payload(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    return client.get(path, params=params or {})


def _render_query_page(
    path: str,
    title: str,
    builder: Callable[[dict[str, Any]], Any],
    renderer: Callable[[Any], str],
    params: dict[str, Any] | None = None,
) -> HTMLResponse:
    data = _payload(path, params)
    page = builder(data)
    sync = deterministic_poll({"items": page.items})
    summary = {**page.summary, **page.timings, "sync_items": sync["item_count"]}
    return _wrap(title, renderer(page), summary)


@router.get("", response_class=HTMLResponse)
def ui_overview(limit: int = Query(default=25, ge=1, le=500)) -> HTMLResponse:
    service = _payload("/runtime/service", {"limit": limit, "offset": 0})
    verification = _payload("/runtime/verification", {"limit": limit, "offset": 0})
    convergence = _payload("/runtime/convergence", {"limit": limit, "offset": 0})
    replay = _payload("/runtime/replay", {"limit": limit, "offset": 0})
    items = (
        service["payload"].get("items", [])
        + verification["payload"].get("items", [])[:5]
        + convergence["payload"].get("items", [])[:5]
        + replay["payload"].get("items", [])[:5]
    )
    sync = deterministic_poll({"items": items})
    body = "<h2>Runtime Overview</h2><p>runtime truth + service + convergence + verification + replay</p>" + render_items_table(sync["items"], limit=limit)
    return _wrap(
        "Runtime Overview",
        body,
        {
            "service_total": service["payload"].get("total", 0),
            "verification_total": verification["payload"].get("total", 0),
            "convergence_total": convergence["payload"].get("total", 0),
            "replay_total": replay["payload"].get("total", 0),
            "sync_items": sync["item_count"],
        },
    )


@router.get("/verification", response_class=HTMLResponse)
def ui_verification(limit: int = Query(default=25, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> HTMLResponse:
    return _render_query_page("/runtime/verification", "Verification State", build_verification_payload, render_verification_view, {"limit": limit, "offset": offset})


@router.get("/convergence", response_class=HTMLResponse)
def ui_convergence(limit: int = Query(default=25, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> HTMLResponse:
    return _render_query_page("/runtime/convergence", "Convergence State", build_convergence_payload, render_convergence_view, {"limit": limit, "offset": offset})


@router.get("/graph", response_class=HTMLResponse)
def ui_graph(limit: int = Query(default=25, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> HTMLResponse:
    return _render_query_page("/runtime/graph", "Runtime Graph", build_graph_payload, render_graph_view, {"limit": limit, "offset": offset})


@router.get("/timeline", response_class=HTMLResponse)
def ui_timeline(limit: int = Query(default=25, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> HTMLResponse:
    return _render_query_page("/runtime/timeline", "Timeline Explorer", build_timeline_payload, render_timeline_view, {"limit": limit, "offset": offset})


@router.get("/evidence", response_class=HTMLResponse)
def ui_evidence(limit: int = Query(default=25, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> HTMLResponse:
    return _render_query_page("/runtime/evidence", "Evidence Explorer", build_evidence_payload, render_evidence_view, {"limit": limit, "offset": offset})


@router.get("/replay", response_class=HTMLResponse)
def ui_replay(limit: int = Query(default=25, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> HTMLResponse:
    return _render_query_page("/runtime/replay", "Replay Explorer", build_replay_payload, render_replay_view, {"limit": limit, "offset": offset})


@router.get("/sessions", response_class=HTMLResponse)
def ui_sessions(limit: int = Query(default=25, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> HTMLResponse:
    return _render_query_page("/runtime/service", "Session State", build_sessions_payload, render_session_view, {"limit": limit, "offset": offset})


@router.get("/service", response_class=HTMLResponse)
def ui_service(limit: int = Query(default=25, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> HTMLResponse:
    return _render_query_page("/runtime/service", "Service Coordination", build_sessions_payload, render_session_view, {"limit": limit, "offset": offset})


@router.get("/diagnostics", response_class=HTMLResponse)
def ui_diagnostics(limit: int = Query(default=25, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> HTMLResponse:
    return _render_query_page("/runtime/service", "Diagnostics", build_diagnostics_payload, render_diagnostics_view, {"limit": limit, "offset": offset})


@router.get("/drift", response_class=HTMLResponse)
def ui_drift(limit: int = Query(default=25, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> HTMLResponse:
    return _render_query_page("/runtime/drift", "Runtime Drift", build_timeline_payload, render_timeline_view, {"limit": limit, "offset": offset})


@router.get("/synchronization", response_class=HTMLResponse)
def ui_synchronization(limit: int = Query(default=25, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> HTMLResponse:
    data = _payload("/runtime/service", {"limit": limit, "offset": offset})
    items = deterministic_poll(data["payload"])["items"]
    body = "<h2>Synchronization State</h2><p>deterministic poll replay-safe stable ordering</p>" + render_items_table(items, limit=limit)
    return _wrap("Synchronization State", body, {"items": len(items), "api_ms": float(data.get("duration_ms", 0.0))})
