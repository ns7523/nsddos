"""Tests for container-aware health checks."""

from __future__ import annotations

import nsddos.health_checks as health_checks
from nsddos.runtime.models import HealthResult, ServiceState


class _StubProvider:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def status(self) -> dict[str, object]:
        return dict(self.payload)


def test_collect_static_health_only_checks_orchestration_prereqs(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(
        "nsddos.health_checks.which",
        lambda name: "/usr/bin/docker" if name == "docker" else None,
    )
    monkeypatch.setattr(
        "nsddos.health_checks.load_config", lambda: {"api_port": 8011, "lab": {}}
    )
    monkeypatch.setattr(
        "nsddos.health_checks.ensure_runtime_directories",
        lambda: (tmp_path / "runtime",),
    )

    results = {item.name: item for item in health_checks.collect_static_health()}

    assert "mininet_binary" not in results
    assert "ovs_vswitch" not in results
    assert results["docker"].ok is True
    assert results["runtime_assets"].category == "static"


def test_collect_runtime_health_requires_exact_stack_containers_only(
    monkeypatch,
) -> None:
    services = [
        ServiceState(name="labhost", status="running", healthy=True, detail="healthy"),
        ServiceState(
            name="floodlight", status="running", healthy=True, detail="healthy"
        ),
        ServiceState(name="sflowrt", status="running", healthy=True, detail="healthy"),
        ServiceState(name="detector", status="running", healthy=True, detail="healthy"),
        ServiceState(name="unrelated", status="exited", healthy=False, detail="exited"),
    ]
    monkeypatch.setattr("nsddos.health_checks.check_docker_daemon", lambda: True)
    monkeypatch.setattr(
        "nsddos.health_checks.DockerManager",
        lambda: type(
            "Docker",
            (),
            {
                "stack_health": lambda self, required: (
                    True,
                    "nsddos-floodlight:healthy, nsddos-sflowrt:healthy, nsddos-labhost:healthy, nsddos-detector:healthy",
                    services,
                )
            },
        )(),
    )
    monkeypatch.setattr(
        "nsddos.health_checks.FloodlightProvider",
        lambda: _StubProvider({"reachable": True, "endpoint": "http://127.0.0.1:8080"}),
    )
    monkeypatch.setattr(
        "nsddos.health_checks.SFlowProvider",
        lambda: _StubProvider({"reachable": True, "endpoint": "http://127.0.0.1:8008"}),
    )
    monkeypatch.setattr(
        "nsddos.health_checks.MininetProvider",
        lambda: _StubProvider(
            {
                "installed": True,
                "controller_reachable": True,
                "controller": "floodlight:6653",
                "running": True,
                "ready": True,
                "detail": "controller=floodlight:6653",
            }
        ),
    )
    monkeypatch.setattr(
        "nsddos.health_checks.OVSProvider",
        lambda: _StubProvider({"ready": True, "detail": "ovs-vswitchd running"}),
    )
    results = {item.name: item for item in health_checks.collect_runtime_health()}

    assert results["containers"].ok is True
    assert "nsddos-labhost:healthy" in results["containers"].detail
    assert results["mininet"].ok is True
    assert results["mininet"].detail == "controller=floodlight:6653"
    assert results["ovs"].ok is True
    assert results["ovs"].detail == "ovs-vswitchd running"


def test_collect_runtime_health_fails_when_required_container_missing(
    monkeypatch,
) -> None:
    services = [
        ServiceState(
            name="floodlight", status="running", healthy=True, detail="healthy"
        ),
        ServiceState(name="sflowrt", status="running", healthy=True, detail="healthy"),
        ServiceState(name="detector", status="running", healthy=True, detail="healthy"),
    ]
    monkeypatch.setattr("nsddos.health_checks.check_docker_daemon", lambda: True)
    monkeypatch.setattr(
        "nsddos.health_checks.DockerManager",
        lambda: type(
            "Docker",
            (),
            {
                "stack_health": lambda self, required: (
                    False,
                    "nsddos-labhost:missing, nsddos-floodlight:healthy, nsddos-sflowrt:healthy, nsddos-detector:healthy",
                    services,
                )
            },
        )(),
    )
    monkeypatch.setattr(
        "nsddos.health_checks.FloodlightProvider",
        lambda: _StubProvider({"reachable": True, "endpoint": "http://127.0.0.1:8080"}),
    )
    monkeypatch.setattr(
        "nsddos.health_checks.SFlowProvider",
        lambda: _StubProvider({"reachable": True, "endpoint": "http://127.0.0.1:8008"}),
    )
    monkeypatch.setattr(
        "nsddos.health_checks.MininetProvider",
        lambda: _StubProvider(
            {
                "installed": False,
                "controller_reachable": False,
                "controller": "floodlight:6653",
                "ready": False,
                "detail": "labhost unavailable",
            }
        ),
    )
    monkeypatch.setattr(
        "nsddos.health_checks.OVSProvider",
        lambda: _StubProvider({"ready": True, "detail": "ovs-vswitchd running"}),
    )

    results = {item.name: item for item in health_checks.collect_runtime_health()}

    assert results["containers"].ok is False
    assert "nsddos-labhost:missing" in results["containers"].detail


def test_deployment_health_uses_corrected_helper_aware_results(monkeypatch) -> None:
    monkeypatch.setattr(
        "nsddos.deployment.healthcheck.DockerManager.is_docker_installed",
        lambda self: True,
    )
    monkeypatch.setattr(
        "nsddos.deployment.healthcheck.DockerManager.is_daemon_running",
        lambda self: True,
    )
    monkeypatch.setattr(
        "nsddos.deployment.healthcheck.DockerManager.compose_exists", lambda self: True
    )
    monkeypatch.setattr(
        "nsddos.deployment.healthcheck.collect_static_health",
        lambda: [
            HealthResult("docker", True, "ok", "static"),
            HealthResult("compose", True, "ok", "static"),
            HealthResult("runtime_assets", True, "ok", "static"),
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
