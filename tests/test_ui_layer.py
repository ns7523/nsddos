"""UI integration and determinism tests."""

from __future__ import annotations

from fastapi.testclient import TestClient
import typer

from nsddos.cli import ui_start
from nsddos.ui.app import create_ui_app, explain_ui
from nsddos.ui.synchronization import deterministic_poll


def _stub_payload(*_args, **_kwargs) -> dict:
    return {"payload": {"items": [], "total": 0}, "duration_ms": 0.0}


def test_ui_routes_render(monkeypatch) -> None:
    monkeypatch.setattr("nsddos.ui.router._payload", _stub_payload)
    with TestClient(create_ui_app()) as client:
        html_routes = {
            "/",
            "/dashboard",
            "/docs",
            "/ui",
            "/ui/verification",
            "/ui/convergence",
            "/ui/graph",
            "/ui/timeline",
            "/ui/evidence",
            "/ui/replay",
            "/ui/sessions",
            "/ui/service",
            "/ui/diagnostics",
            "/ui/drift",
            "/ui/synchronization",
        }
        for path in (
            "/",
            "/dashboard",
            "/favicon.ico",
            "/health",
            "/runtime/detection",
            "/runtime/mitigation",
            "/docs",
            "/ui",
            "/ui/verification",
            "/ui/convergence",
            "/ui/graph",
            "/ui/timeline",
            "/ui/evidence",
            "/ui/replay",
            "/ui/sessions",
            "/ui/service",
            "/ui/diagnostics",
            "/ui/drift",
            "/ui/synchronization",
        ):
            response = client.get(path, follow_redirects=True)
            assert response.status_code == 200
            if path == "/favicon.ico":
                continue
            if path in html_routes:
                assert "<html>" in response.text or "openapi" in response.text.lower()
            else:
                assert response.headers["content-type"].startswith("application/json")


def test_ui_route_presence() -> None:
    paths = {route.path for route in create_ui_app().routes}
    assert "/" in paths
    assert "/dashboard" in paths
    assert "/favicon.ico" in paths


def test_ui_root_control_panel() -> None:
    with TestClient(create_ui_app()) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "NSDDOS Control Panel" in response.text
        assert "/dashboard" in response.text
        assert "/health" in response.text
        assert "/runtime/service" in response.text
        assert "/runtime/detection" in response.text
        assert "/runtime/mitigation" in response.text
        assert "/docs" in response.text


def test_ui_deterministic_ordering() -> None:
    items = [{"id": "z"}, {"id": "a"}, {"id": "m"}]
    synchronized = deterministic_poll({"items": items})
    ordered = [item["id"] for item in synchronized["items"]]
    assert ordered == ["a", "m", "z"]


def test_ui_replay_safe_pagination(monkeypatch) -> None:
    monkeypatch.setattr("nsddos.ui.router._payload", _stub_payload)
    with TestClient(create_ui_app()) as client:
        response = client.get("/ui/replay", params={"limit": 2, "offset": 0})
        assert response.status_code == 200
        assert "Replay Explorer" in response.text


def test_ui_graph_and_convergence_rendering(monkeypatch) -> None:
    monkeypatch.setattr("nsddos.ui.router._payload", _stub_payload)
    with TestClient(create_ui_app()) as client:
        graph = client.get("/ui/graph", params={"limit": 5, "offset": 0})
        convergence = client.get("/ui/convergence", params={"limit": 5, "offset": 0})
        assert graph.status_code == 200
        assert convergence.status_code == 200
        assert "Runtime Graph" in graph.text
        assert "Convergence State" in convergence.text


def test_ui_evidence_and_synchronization_rendering(monkeypatch) -> None:
    monkeypatch.setattr("nsddos.ui.router._payload", _stub_payload)
    with TestClient(create_ui_app()) as client:
        evidence = client.get("/ui/evidence", params={"limit": 5, "offset": 0})
        sync = client.get("/ui/synchronization", params={"limit": 5, "offset": 0})
        assert evidence.status_code == 200
        assert sync.status_code == 200
        assert "Evidence Explorer" in evidence.text
        assert "Synchronization State" in sync.text


def test_ui_explain_contract() -> None:
    explanation = explain_ui()
    assert explanation["readonly"] is True
    assert explanation["query_backed"] is True
    assert explanation["api_only"] is True
    assert explanation["replay_safe"] is True
    assert "verification" in explanation["surfaces"]


def test_ui_start_opens_root_url(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class ImmediateTimer:
        def __init__(self, interval, fn):
            calls["interval"] = interval
            calls["timer_fn"] = fn

        def start(self):
            fn = calls.get("timer_fn")
            if callable(fn):
                fn()

    def fake_run(target: str, host: str, port: int, reload: bool) -> None:
        calls["target"] = target
        calls["host"] = host
        calls["port"] = port
        calls["reload"] = reload
        raise KeyboardInterrupt()

    monkeypatch.setattr("nsddos.cli.threading.Timer", ImmediateTimer)
    monkeypatch.setattr("nsddos.cli.webbrowser.open", lambda url: calls.setdefault("url", url))
    monkeypatch.setattr("uvicorn.run", fake_run)

    try:
        ui_start(host="127.0.0.1", port=8010)
    except typer.Exit:
        assert False, "ui_start should not exit on KeyboardInterrupt"

    assert calls["url"] == "http://127.0.0.1:8010/"
    assert calls["target"] == "nsddos.ui.app:app"
    assert calls["host"] == "127.0.0.1"
    assert calls["port"] == 8010
    assert calls["reload"] is False
