"""UI integration and determinism tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from nsddos.bootstrap.state import DiagnosticFinding, StartupPortBinding, StartupSession
from nsddos.bootstrap.ui_launcher import (
    launch_ui_background,
    replace_listener_on_port,
    ui_is_modern,
)
from nsddos.cli import ui_start
from nsddos.ui.api_client import UiApiClient
from nsddos.ui.app import create_ui_app, explain_ui
from nsddos.ui.dashboard_pages import UiPageBuilder
from nsddos.ui.models import (
    UiPagePayload,
    UiPageSnapshot,
    UiStatusBarSnapshot,
    UiStatusField,
)


def _dashboard_payload() -> dict:
    return {
        "dashboard_id": "dash-1",
        "active_attacks": 3,
        "active_alerts": 4,
        "stream_throughput": 91.2,
        "cluster_nodes": 2,
        "ml_confidence": 0.91,
        "mitigation_events": 7,
        "policy_events": 5,
        "dashboard_health": "healthy",
        "timestamp": "2026-06-22T10:00:00Z",
        "metrics": {"packet_throughput": 4382.0, "byte_throughput": 8192.0},
        "streams": {"active_streams": 1, "queue_depth": 2},
        "attacks": {
            "attack_types": [["syn_flood", 2], ["udp_flood", 1]],
            "source_ips": [["10.0.0.4", 4], ["10.0.0.5", 2]],
        },
        "threat_intel": {
            "suspicious_protocol_concentration": [["tcp", 0.7], ["udp", 0.3]]
        },
        "visualizations": [
            {
                "chart_id": "throughput",
                "title": "Throughput",
                "points": [
                    ["t-4", 2100],
                    ["t-3", 2400],
                    ["t-2", 3000],
                    ["t-1", 4100],
                    ["now", 4382],
                ],
            },
        ],
    }


def _fake_api(_self, path: str, params: dict | None = None) -> dict:
    payloads = {
        "/runtime/detection": {
            "attack_detected": True,
            "attack_type": "syn_flood",
            "confidence": 0.98,
            "risk_level": "low",
        },
        "/runtime/mitigation": {
            "mitigation_required": True,
            "mitigation_action": "rate_limit",
            "target_ip": "10.0.0.4",
            "execution_result": "applied",
        },
        "/runtime/ml/infer": {
            "predicted_attack_type": "syn_flood",
            "confidence_score": 0.95,
            "anomaly_score": 0.87,
            "drift_score": 0.14,
        },
        "/runtime/live-telemetry": {
            "provider_source": "sflowrt",
            "packet_rate": 4382.0,
            "byte_rate": 12288.0,
            "active_flows": 12,
            "health_state": "healthy",
            "controller_status": "running",
            "timestamp": "2026-06-22T10:00:20Z",
        },
        "/health": {
            "status": "healthy",
            "checks": {
                "docker": True,
                "docker_daemon": True,
                "floodlight": True,
                "sflowrt": True,
                "mininet": True,
                "ovs": True,
            },
        },
        "/runtime/provider-health": {
            "items": [
                {
                    "id": "provider-floodlight",
                    "provider_name": "Floodlight",
                    "health_state": "healthy",
                    "detail": "controller online",
                },
                {
                    "id": "provider-sflowrt",
                    "provider_name": "sFlowRT",
                    "health_state": "healthy",
                    "detail": "telemetry online",
                },
            ],
            "total": 2,
            "replay_safe": True,
            "timestamp": "2026-06-22T10:00:20Z",
        },
        "/runtime/service": {
            "items": [
                {
                    "id": "service-state",
                    "kind": "service",
                    "state": "active",
                    "owner": "runtime",
                },
                {
                    "id": "session-1",
                    "kind": "session",
                    "state": "active",
                    "owner": "ops",
                },
            ],
            "total": 2,
            "replay_safe": True,
            "timestamp": "2026-06-22T10:00:20Z",
        },
        "/dashboard/report": {
            "reports": [
                {
                    "report_type": "mitigation_posture",
                    "summary": "rate limiting active",
                    "timestamp": "2026-06-22T10:00:30Z",
                }
            ]
        },
        "/dashboard/diagnostics": {"diagnostics": {"dashboard_latency_ms": 8.2}},
        "/runtime/verification": {
            "items": [{"id": "verify-1", "category": "runtime", "status": "pass"}],
            "total": 1,
            "replay_safe": True,
            "timestamp": "2026-06-22T10:00:20Z",
        },
        "/runtime/convergence": {
            "items": [{"id": "conv-1", "state": "stable"}],
            "total": 1,
            "replay_safe": True,
            "timestamp": "2026-06-22T10:00:20Z",
        },
        "/runtime/graph": {
            "items": [{"id": "node-1", "label": "switch-1"}],
            "total": 1,
            "replay_safe": True,
            "timestamp": "2026-06-22T10:00:20Z",
        },
        "/runtime/timeline": {
            "items": [{"id": "time-1", "event_type": "start"}],
            "total": 1,
            "replay_safe": True,
            "timestamp": "2026-06-22T10:00:20Z",
        },
        "/runtime/evidence": {
            "items": [{"id": "ev-1", "kind": "bundle"}],
            "total": 1,
            "replay_safe": True,
            "timestamp": "2026-06-22T10:00:20Z",
        },
        "/runtime/replay": {
            "items": [{"id": "rep-1", "kind": "replay"}],
            "total": 1,
            "replay_safe": True,
            "timestamp": "2026-06-22T10:00:20Z",
        },
        "/runtime/drift": {
            "items": [{"id": "drift-1", "state": "low"}],
            "total": 1,
            "replay_safe": True,
            "timestamp": "2026-06-22T10:00:20Z",
        },
    }
    return {"payload": payloads[path], "duration_ms": 1.2}


def _stub_ui_sources(
    monkeypatch, *, startup_session: StartupSession | None = None
) -> None:
    monkeypatch.setattr("nsddos.ui.dashboard_pages.UiPageBuilder._api", _fake_api)
    monkeypatch.setattr(
        "nsddos.ui.dashboard_pages.generate_dashboard_state",
        lambda config: type(
            "Evaluation", (), {"to_dict": lambda self: _dashboard_payload()}
        )(),
    )
    monkeypatch.setattr(
        "nsddos.ui.dashboard_pages.latest_history_payload",
        lambda: {
            "attack_history": [
                {
                    "event_type": "attack_detection",
                    "severity": "alert",
                    "detail": "syn flood detected",
                    "timestamp": "2026-06-22T10:00:00Z",
                }
            ],
            "mitigation_history": [
                {
                    "event_type": "mitigation",
                    "severity": "warn",
                    "detail": "rate limit applied",
                    "timestamp": "2026-06-22T10:00:10Z",
                }
            ],
            "cluster_history": [
                {
                    "event_type": "runtime",
                    "severity": "info",
                    "detail": "heartbeat",
                    "timestamp": "2026-06-22T10:00:20Z",
                }
            ],
        },
    )
    monkeypatch.setattr(
        "nsddos.ui.dashboard_pages.collect_service_diagnostics",
        lambda: {
            "active_sessions": [{"session_id": "session-1", "state": "active"}],
            "session_count": 1,
            "heartbeat_count": 4,
            "replay": {"event_count": 2},
            "synchronization": {"state": "aligned"},
        },
    )
    monkeypatch.setattr(
        "nsddos.ui.dashboard_pages.load_startup_session", lambda: startup_session
    )
    monkeypatch.setattr(
        "nsddos.ui.dashboard_pages.collect_diagnostic_findings",
        lambda: (
            DiagnosticFinding(
                "docker",
                "docker_daemon",
                "fail",
                "Stopped",
                repairable=True,
                critical=True,
            ),
            DiagnosticFinding(
                "runtime",
                "ovs",
                "fail",
                "Missing bridge",
                repairable=True,
                critical=True,
            ),
        ),
    )


def test_ui_routes_render_cyber_console(monkeypatch) -> None:
    _stub_ui_sources(
        monkeypatch,
        startup_session=StartupSession(
            "2026-06-22T10:00:00Z",
            ("nsddos-floodlight",),
            (StartupPortBinding("ui", 8010),),
            "healthy",
            "http://127.0.0.1:8010",
        ),
    )
    with TestClient(create_ui_app()) as client:
        html_routes = {
            "/",
            "/dashboard",
            "/ui",
            "/ui/infrastructure",
            "/ui/detection",
            "/ui/mitigation",
            "/ui/live-traffic",
            "/ui/attack-logs",
            "/ui/doctor",
            "/ui/session",
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
        for path in html_routes:
            response = client.get(path, follow_redirects=True)
            assert response.status_code == 200
            assert "NSDDOS" in response.text
            assert "ENTERPRISE CYBER DEFENSE DASHBOARD" in response.text
            assert "COMMAND CENTER" in response.text


def test_ui_route_presence() -> None:
    paths = {route.path for route in create_ui_app().routes}
    assert "/" in paths
    assert "/dashboard" in paths
    assert "/ui/attack-logs" in paths
    assert "/ui/ws/attack-logs" in paths
    assert "/ui/healthz" in paths
    assert "/favicon.ico" in paths


def test_ui_favicon_serves_real_asset(monkeypatch) -> None:
    _stub_ui_sources(monkeypatch)
    with TestClient(create_ui_app()) as client:
        response = client.get("/favicon.ico")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/svg+xml")
        assert response.content.startswith(b"<svg")


def test_ui_root_redesign_markers(monkeypatch) -> None:
    _stub_ui_sources(monkeypatch)
    with TestClient(create_ui_app()) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "SYSTEM" in response.text
        assert "THREAT LEVEL" in response.text
        assert "ATTACK SIMULATOR" in response.text
        assert "MISSION CONTROL" in response.text
        assert "SERVICE STATUS MATRIX" in response.text


def test_overview_view_model_has_fixed_attack_order(monkeypatch) -> None:
    _stub_ui_sources(monkeypatch)
    page = UiPageBuilder().overview()

    assert [point.label for point in page.attack_chart.points] == [
        "SYN Flood",
        "UDP Flood",
        "ICMP Flood",
        "HTTP Flood",
        "Slowloris",
    ]
    assert [point.value for point in page.attack_chart.points] == [
        2.0,
        1.0,
        0.0,
        0.0,
        0.0,
    ]


def test_status_bar_has_exact_five_fields_and_uptime_fallback(monkeypatch) -> None:
    _stub_ui_sources(monkeypatch, startup_session=None)
    page = UiPageBuilder().overview()

    assert [field.label for field in page.status_bar.fields] == [
        "SYSTEM",
        "THREAT LEVEL",
        "UPTIME",
        "PACKETS/S",
        "ACTIVE ATTACKS",
    ]
    assert page.status_bar.fields[2].value == "--:--"


def test_attack_logs_feed_is_merged_in_reverse_time_order(monkeypatch) -> None:
    _stub_ui_sources(monkeypatch)
    page = UiPageBuilder().attack_logs()

    assert [entry.source for entry in page.feed.entries] == [
        "RUNTIME",
        "MITIGATION",
        "DETECTION",
    ]
    assert page.feed.entries[0].message == "heartbeat"


def test_topology_contains_canonical_nodes(monkeypatch) -> None:
    _stub_ui_sources(monkeypatch)
    page = UiPageBuilder().overview()

    assert {node.label for node in page.topology.nodes} == {
        "INTERNET",
        "ROUTER",
        "FLOODLIGHT",
        "SFLOWRT",
        "OVS SWITCH",
        "h1",
        "h2",
        "h3",
        "DETECTION",
        "MITIGATION",
    }
    assert all(edge.pulse for edge in page.topology.edges if edge.state == "ONLINE")


def test_ui_doctor_page_renders_cli_cta(monkeypatch) -> None:
    _stub_ui_sources(monkeypatch)
    with TestClient(create_ui_app()) as client:
        response = client.get("/ui/doctor")
        assert response.status_code == 200
        assert "nsddos doctor" in response.text
        assert "WEB UI IS READ ONLY" in response.text


def test_ui_session_page_handles_missing_startup_session(monkeypatch) -> None:
    _stub_ui_sources(monkeypatch, startup_session=None)
    with TestClient(create_ui_app()) as client:
        response = client.get("/ui/session")
        assert response.status_code == 200
        assert "NO STARTUP SESSION RECORDED." in response.text


def test_ui_assets_served(monkeypatch) -> None:
    _stub_ui_sources(monkeypatch)
    with TestClient(create_ui_app()) as client:
        css = client.get("/static/css/app.css")
        js = client.get("/static/js/charts.js")
        topology = client.get("/static/js/topology.js")
        vendor = client.get("/static/vendor/cytoscape.min.js")
        font = client.get("/static/fonts/JetBrainsMono-Regular.ttf")
        assert css.status_code == 200
        assert js.status_code == 200
        assert topology.status_code == 200
        assert vendor.status_code == 200
        assert font.status_code == 200
        assert "@font-face" in css.text
        assert "window.nsddosCharts" in js.text
        assert "window.nsddosTopology" in topology.text
        assert "tailwind" not in css.text.lower()


def test_ui_healthz_returns_fast_ok() -> None:
    with TestClient(create_ui_app()) as client:
        response = client.get("/ui/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_ui_websocket_overview_snapshot(monkeypatch) -> None:
    snapshot = UiPageSnapshot(
        status="ok",
        page=UiPagePayload(
            name="overview",
            title="OVERVIEW",
            description="LIVE RUNTIME TELEMETRY",
            active_path="/ui",
            status_bar=UiStatusBarSnapshot(
                fields=(
                    UiStatusField("SYSTEM", "ONLINE", "good"),
                    UiStatusField("THREAT LEVEL", "LOW", "good"),
                    UiStatusField("UPTIME", "--:--"),
                    UiStatusField("PACKETS/S", "4382"),
                    UiStatusField("ACTIVE ATTACKS", "0", "good"),
                ),
            ),
        ),
    )
    monkeypatch.setattr("nsddos.ui.router.builder.snapshot_for", lambda name: snapshot)
    with TestClient(create_ui_app()) as client:
        with client.websocket_connect("/ui/ws/overview") as websocket:
            payload = websocket.receive_json()
            assert payload["status"] == "ok"
            assert payload["page"]["name"] == "overview"
            assert payload["page"]["status_bar"]["fields"][0]["label"] == "SYSTEM"


def test_ui_websocket_attack_logs_snapshot(monkeypatch) -> None:
    snapshot = UiPageSnapshot(
        status="ok",
        page=UiPagePayload(
            name="attack-logs",
            title="ATTACK LOGS",
            description="MERGED FEED",
            active_path="/ui/attack-logs",
            status_bar=UiStatusBarSnapshot(
                fields=(
                    UiStatusField("SYSTEM", "ONLINE", "good"),
                    UiStatusField("THREAT LEVEL", "LOW", "good"),
                    UiStatusField("UPTIME", "--:--"),
                    UiStatusField("PACKETS/S", "4382"),
                    UiStatusField("ACTIVE ATTACKS", "0", "good"),
                ),
            ),
        ),
    )
    monkeypatch.setattr("nsddos.ui.router.builder.snapshot_for", lambda name: snapshot)
    with TestClient(create_ui_app()) as client:
        with client.websocket_connect("/ui/ws/attack-logs") as websocket:
            payload = websocket.receive_json()
            assert payload["page"]["name"] == "attack-logs"


def test_attack_simulator_route_shows_expected_controls(monkeypatch) -> None:
    _stub_ui_sources(monkeypatch)
    with TestClient(create_ui_app()) as client:
        response = client.get("/ui/attack-logs")

    assert response.status_code == 200
    assert "Launch SYN Flood" in response.text
    assert "Launch UDP Flood" in response.text
    assert "Launch ICMP Flood" in response.text


def test_ui_signature_detection(monkeypatch) -> None:
    monkeypatch.setattr(
        "nsddos.bootstrap.ui_launcher._fetch_ui_html",
        lambda url: "<html><title>OVERVIEW | NSDDOS</title><link rel='stylesheet' href='/static/css/app.css'><div>NSDDOS</div><div>SYSTEM</div><div>THREAT LEVEL</div></html>",
    )

    assert ui_is_modern("http://127.0.0.1:8010") is True


def test_ui_api_client_returns_fallback_payload_on_timeout(monkeypatch) -> None:
    client = UiApiClient()
    monkeypatch.setattr(
        client,
        "_request_with_timeout",
        lambda path, params: (_ for _ in ()).throw(TimeoutError("stalled")),
    )

    result = client.get("/runtime/detection")

    assert result["payload"]["attack_type"] == "unknown"
    assert result["payload"]["detail"] == "stalled"


def test_replace_listener_on_port_terminates_pids(monkeypatch) -> None:
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(
        "nsddos.bootstrap.ui_launcher.subprocess.run",
        lambda *args, **kwargs: type(
            "Completed", (), {"returncode": 0, "stdout": "111\n222\n"}
        )(),
    )
    monkeypatch.setattr(
        "nsddos.bootstrap.ui_launcher.os.kill",
        lambda pid, sig: calls.append((pid, sig)),
    )

    terminated = replace_listener_on_port(8010, exclude_pid=222)

    assert terminated == (111,)
    assert calls == [(111, 15)]


def test_launch_ui_background_restarts_stale_ui(monkeypatch) -> None:
    state = {"calls": 0}

    def fake_reachable(_url: str) -> bool:
        state["calls"] += 1
        return state["calls"] != 2

    monkeypatch.setattr("nsddos.bootstrap.ui_launcher.ui_reachable", fake_reachable)
    monkeypatch.setattr("nsddos.bootstrap.ui_launcher.ui_is_modern", lambda url: False)
    monkeypatch.setattr(
        "nsddos.bootstrap.ui_launcher.replace_listener_on_port", lambda port: (98765,)
    )
    monkeypatch.setattr("nsddos.bootstrap.ui_launcher.time.sleep", lambda *_args: None)
    monkeypatch.setattr(
        "nsddos.bootstrap.ui_launcher.subprocess.Popen",
        lambda *args, **kwargs: object(),
    )

    result = launch_ui_background()

    assert result.launched is True
    assert result.reachable is True


def test_ui_explain_contract() -> None:
    explanation = explain_ui()
    assert explanation["readonly"] is True
    assert explanation["query_backed"] is True
    assert explanation["api_only"] is True
    assert explanation["replay_safe"] is True
    assert "/ui/attack-logs" in explanation["surfaces"]


def test_ui_start_opens_root_url(monkeypatch) -> None:
    calls: dict[str, object] = {}
    import nsddos.cli as cli_module

    class ImmediateTimer:
        def __init__(self, interval, fn):
            calls["interval"] = interval
            calls["timer_fn"] = fn

        def start(self):
            fn = calls.get("timer_fn")
            if callable(fn):
                fn()

    monkeypatch.setattr(cli_module.threading, "Timer", ImmediateTimer)
    monkeypatch.setattr(
        cli_module.webbrowser, "open", lambda url: calls.setdefault("url", url)
    )
    monkeypatch.setattr(
        cli_module.uvicorn,
        "run",
        lambda *args, **kwargs: calls.setdefault("served", True),
    )

    try:
        ui_start(host="127.0.0.1", port=8010)
    except SystemExit:
        pass

    assert calls["url"] == "http://127.0.0.1:8010/"
