"""Tests for helper-aware health checks."""

from __future__ import annotations

import subprocess

from nsddos.runtime.models import HealthResult, ServiceState


class _StubProvider:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def status(self) -> dict[str, object]:
        return dict(self.payload)


def test_collect_static_health_prefers_helper_container_for_mininet_and_ovs(monkeypatch, tmp_path) -> None:
    missing_mininet = tmp_path / "missing-mn"
    monkeypatch.setattr("nsddos.health.MININET_BIN", missing_mininet)
    monkeypatch.setattr("nsddos.health.which", lambda name: "/usr/bin/docker" if name == "docker" else None)
    monkeypatch.setattr("nsddos.health.load_config", lambda: {"api_port": 8011, "lab": {}})
    monkeypatch.setattr("nsddos.health.ensure_runtime_directories", lambda: (tmp_path / "runtime",))
    monkeypatch.setattr("nsddos.health.helper_running", lambda: True)
    monkeypatch.setattr("nsddos.health.OVSProvider.is_installed", staticmethod(lambda: True))

    def fake_helper_exec(args, timeout=5):
        if args == ["which", "mn"]:
            return subprocess.CompletedProcess(args, 0, stdout="/usr/bin/mn\n", stderr="")
        if args == ["ovs-vsctl", "show"]:
            return subprocess.CompletedProcess(args, 0, stdout="connected to /var/run/openvswitch/db.sock\n", stderr="")
        raise AssertionError(f"unexpected helper command: {args}")

    monkeypatch.setattr("nsddos.health.helper_exec", fake_helper_exec)

    results = {item.name: item for item in __import__("nsddos.health", fromlist=["collect_static_health"]).collect_static_health()}

    assert results["mininet_binary"].ok is True
    assert results["mininet_binary"].detail == "/usr/bin/mn"
    assert results["ovs_vswitch"].ok is True
    assert "openvswitch/db.sock" in results["ovs_vswitch"].detail


def test_collect_runtime_health_requires_exact_stack_containers_only(monkeypatch) -> None:
    services = [
        ServiceState(name="labhost", status="running", healthy=True, detail="healthy"),
        ServiceState(name="floodlight", status="running", healthy=True, detail="healthy"),
        ServiceState(name="sflowrt", status="running", healthy=True, detail="healthy"),
        ServiceState(name="detector", status="running", healthy=True, detail="healthy"),
        ServiceState(name="unrelated", status="exited", healthy=False, detail="exited"),
    ]
    monkeypatch.setattr("nsddos.health.check_docker_daemon", lambda: True)
    monkeypatch.setattr("nsddos.health.DockerManager", lambda: type("Docker", (), {"get_service_states": lambda self: services})())
    monkeypatch.setattr(
        "nsddos.health.FloodlightProvider",
        lambda: _StubProvider({"reachable": True, "endpoint": "http://127.0.0.1:8080"}),
    )
    monkeypatch.setattr(
        "nsddos.health.SFlowProvider",
        lambda: _StubProvider({"reachable": True, "endpoint": "http://127.0.0.1:8008"}),
    )
    monkeypatch.setattr(
        "nsddos.health.MininetProvider",
        lambda: _StubProvider(
            {
                "installed": True,
                "controller_reachable": True,
                "controller": "floodlight:6653",
                "running": False,
            }
        ),
    )
    monkeypatch.setattr(
        "nsddos.health.OVSProvider",
        lambda: _StubProvider({"ready": True, "detail": "ovs-vswitchd running"}),
    )
    monkeypatch.setattr("nsddos.health.helper_running", lambda: True)

    def fake_helper_exec(args, timeout=5):
        if args == ["which", "mn"]:
            return subprocess.CompletedProcess(args, 0, stdout="/usr/bin/mn\n", stderr="")
        if args == ["ovs-vsctl", "show"]:
            return subprocess.CompletedProcess(args, 0, stdout="Bridge s1\n", stderr="")
        raise AssertionError(f"unexpected helper command: {args}")

    monkeypatch.setattr("nsddos.health.helper_exec", fake_helper_exec)

    results = {item.name: item for item in __import__("nsddos.health", fromlist=["collect_runtime_health"]).collect_runtime_health()}

    assert results["containers"].ok is True
    assert "nsddos-labhost:healthy" in results["containers"].detail
    assert results["mininet"].ok is True
    assert "controller=floodlight:6653" in results["mininet"].detail
    assert results["ovs"].ok is True
    assert results["ovs"].detail == "Bridge s1"


def test_collect_runtime_health_fails_when_required_container_missing(monkeypatch) -> None:
    services = [
        ServiceState(name="floodlight", status="running", healthy=True, detail="healthy"),
        ServiceState(name="sflowrt", status="running", healthy=True, detail="healthy"),
        ServiceState(name="detector", status="running", healthy=True, detail="healthy"),
    ]
    monkeypatch.setattr("nsddos.health.check_docker_daemon", lambda: True)
    monkeypatch.setattr("nsddos.health.DockerManager", lambda: type("Docker", (), {"get_service_states": lambda self: services})())
    monkeypatch.setattr(
        "nsddos.health.FloodlightProvider",
        lambda: _StubProvider({"reachable": True, "endpoint": "http://127.0.0.1:8080"}),
    )
    monkeypatch.setattr(
        "nsddos.health.SFlowProvider",
        lambda: _StubProvider({"reachable": True, "endpoint": "http://127.0.0.1:8008"}),
    )
    monkeypatch.setattr(
        "nsddos.health.MininetProvider",
        lambda: _StubProvider({"installed": True, "controller_reachable": True, "controller": "floodlight:6653"}),
    )
    monkeypatch.setattr("nsddos.health.OVSProvider", lambda: _StubProvider({"ready": True, "detail": "ovs-vswitchd running"}))
    monkeypatch.setattr("nsddos.health.helper_running", lambda: True)
    monkeypatch.setattr(
        "nsddos.health.helper_exec",
        lambda args, timeout=5: subprocess.CompletedProcess(args, 0, stdout="/usr/bin/mn\n", stderr="")
        if args == ["which", "mn"]
        else subprocess.CompletedProcess(args, 0, stdout="Bridge s1\n", stderr=""),
    )

    results = {item.name: item for item in __import__("nsddos.health", fromlist=["collect_runtime_health"]).collect_runtime_health()}

    assert results["containers"].ok is False
    assert "nsddos-labhost:missing" in results["containers"].detail


def test_deployment_health_uses_corrected_helper_aware_results(monkeypatch) -> None:
    monkeypatch.setattr("nsddos.deployment.healthcheck.DockerManager.is_docker_installed", lambda self: True)
    monkeypatch.setattr("nsddos.deployment.healthcheck.DockerManager.is_daemon_running", lambda self: True)
    monkeypatch.setattr("nsddos.deployment.healthcheck.DockerManager.compose_exists", lambda self: True)
    monkeypatch.setattr(
        "nsddos.deployment.healthcheck.collect_static_health",
        lambda: [
            HealthResult("docker", True, "ok", "static"),
            HealthResult("compose", True, "ok", "static"),
            HealthResult("mininet_binary", True, "/usr/bin/mn", "static"),
            HealthResult("ovs_vswitch", True, "Bridge s1", "static"),
        ],
    )
    monkeypatch.setattr(
        "nsddos.deployment.healthcheck.collect_runtime_health",
        lambda: [
            HealthResult("docker_daemon", True, "ok", "runtime"),
            HealthResult("containers", True, "ok", "runtime"),
            HealthResult("floodlight", True, "ok", "runtime"),
            HealthResult("sflowrt", True, "ok", "runtime"),
            HealthResult("mininet", True, "ok", "runtime"),
            HealthResult("ovs", True, "ok", "runtime"),
        ],
    )

    state, _latency_ms = __import__(
        "nsddos.deployment.healthcheck",
        fromlist=["compute_deployment_health"],
    ).compute_deployment_health(())

    assert state.state == "healthy"
    assert state.service_health == "healthy"
