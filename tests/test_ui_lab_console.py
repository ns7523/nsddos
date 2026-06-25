from __future__ import annotations

from fastapi.testclient import TestClient

from nsddos.ui.app import create_ui_app
from nsddos.ui.models import (
    UiLabActionButton,
    UiLabActionStatus,
    UiLabConsolePayload,
    UiLabEdge,
    UiLabNode,
    UiLabTelemetryItem,
    UiLabTerminalTab,
    UiPagePayload,
    UiPageSnapshot,
)


def _lab_payload() -> UiPagePayload:
    return UiPagePayload(
        name="lab-console",
        title="LAB CONSOLE",
        eyebrow="Live Mininet Runtime",
        description="Interactive Mininet lab control surface.",
        active_path="/ui/lab-console",
        lab_console=UiLabConsolePayload(
            nodes=(
                UiLabNode(
                    node_id="h1",
                    label="h1",
                    kind="host",
                    state="online",
                    detail="10.0.0.1",
                    metadata={"ip": "10.0.0.1"},
                    actions=("open_shell",),
                ),
                UiLabNode(
                    node_id="mitigation",
                    label="Mitigation engine",
                    kind="service",
                    state="planned",
                    detail="rate_limit",
                    metadata={"mitigation_state": "planned"},
                    actions=("inspect",),
                ),
            ),
            edges=(UiLabEdge(source="h1", target="mitigation", label="observed_by"),),
            telemetry=(
                UiLabTelemetryItem("Packets/sec", "220.0", "Live packet rate", "good"),
                UiLabTelemetryItem(
                    "Mitigation state", "planned", "Latest mitigation state", "warn"
                ),
            ),
            terminal_tabs=(
                UiLabTerminalTab(
                    host="h1", label="h1", state="connected", prompt="h1#"
                ),
                UiLabTerminalTab(host="h2", label="h2", state="idle", prompt="h2#"),
                UiLabTerminalTab(host="h3", label="h3", state="idle", prompt="h3#"),
            ),
            action_buttons=(
                UiLabActionButton("Open h1 shell", "open-h1-shell", "shell"),
                UiLabActionButton("Run SYN Flood", "run-syn-flood", "attack"),
                UiLabActionButton("Run UDP Flood", "run-udp-flood", "attack"),
                UiLabActionButton("Run ICMP Flood", "run-icmp-flood", "attack"),
                UiLabActionButton("Stop attack", "stop-attack", "control"),
            ),
            action_status=UiLabActionStatus(
                action="idle",
                state="ready",
                detail="Awaiting operator command.",
                timestamp="2026-06-23T10:00:00Z",
            ),
        ),
        updated_at="2026-06-23T10:00:00Z",
    )


def test_lab_console_route_renders(monkeypatch) -> None:
    monkeypatch.setattr("nsddos.ui.router.builder.lab_console", _lab_payload)

    with TestClient(create_ui_app()) as client:
        response = client.get("/ui/lab-console")

    assert response.status_code == 200
    assert "LAB CONSOLE" in response.text
    assert "Open h1 shell" in response.text
    assert "Run SYN Flood" in response.text
    assert "Run ICMP Flood" in response.text
    assert "Packets/sec" in response.text


def test_lab_console_snapshot_websocket(monkeypatch) -> None:
    snapshot = UiPageSnapshot(status="ok", page=_lab_payload())
    monkeypatch.setattr("nsddos.ui.router.builder.snapshot_for", lambda name: snapshot)

    with TestClient(create_ui_app()) as client:
        with client.websocket_connect("/ui/ws/lab-console") as websocket:
            payload = websocket.receive_json()

    assert payload["page"]["name"] == "lab-console"
    assert payload["page"]["lab_console"]["nodes"][0]["node_id"] == "h1"
    assert payload["page"]["lab_console"]["telemetry"][0]["label"] == "Packets/sec"


def test_lab_console_terminal_websocket_rejects_invalid_host() -> None:
    with TestClient(create_ui_app()) as client:
        try:
            with client.websocket_connect("/ui/ws/lab-terminal/badhost"):
                pass
        except (
            Exception
        ) as exc:  # pragma: no cover - exact exception type differs by Starlette version
            assert (
                getattr(exc, "code", 0) == 1008
                or "invalid host" in getattr(exc, "reason", "").lower()
            )
        else:  # pragma: no cover
            assert False, "invalid host websocket should reject"


def test_lab_console_terminal_websocket_accepts_valid_host(monkeypatch) -> None:
    monkeypatch.setattr(
        "nsddos.ui.lab_console.terminal_manager.build_command", lambda host: ["/bin/sh"]
    )

    with TestClient(create_ui_app()) as client:
        with client.websocket_connect("/ui/ws/lab-terminal/h1") as websocket:
            websocket.send_text("printf 'lab-ready\\n'\n")
            output = ""
            for _ in range(8):
                chunk = websocket.receive_text()
                output += chunk
                if "lab-ready" in output:
                    break

    assert "lab-ready" in output


def test_lab_console_action_endpoint_dispatches_expected_runtime_helper(
    monkeypatch,
) -> None:
    calls: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        "nsddos.ui.lab_console.control_manager.run_action",
        lambda action, payload=None: calls.append((action, payload or {}))
        or {
            "action": action,
            "state": "started",
            "detail": "ok",
        },
    )

    with TestClient(create_ui_app()) as client:
        response = client.post("/ui/api/lab/actions/run-icmp-flood")

    assert response.status_code == 200
    assert response.json()["action"] == "run-icmp-flood"
    assert calls == [("run-icmp-flood", {})]
