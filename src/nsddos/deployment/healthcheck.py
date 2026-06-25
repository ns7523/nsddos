"""Deterministic deployment health checks."""

from __future__ import annotations

from time import perf_counter

from nsddos.docker_manager import DockerManager
from nsddos.deployment.contracts import ContainerContract, DeploymentHealthState
from nsddos.health_checks import collect_runtime_health, collect_static_health


def compute_deployment_health(container_contracts: tuple[ContainerContract, ...]) -> tuple[DeploymentHealthState, float]:
    """Compute deployment health state without mutating the environment."""
    started = perf_counter()
    manager = DockerManager()
    docker_installed = manager.is_docker_installed()
    docker_daemon = manager.is_daemon_running() if docker_installed else False
    compose_available = manager.compose_exists()
    static_ok = all(item.ok for item in collect_static_health())
    runtime_health = collect_runtime_health()
    runtime_ok = all(item.ok for item in runtime_health)
    environment_ready = static_ok and docker_installed and compose_available
    if environment_ready and docker_daemon and runtime_ok:
        state = "healthy"
        service_health = "healthy"
        detail = f"containers={len(container_contracts)} runtime_checks=ok"
    elif environment_ready:
        state = "degraded"
        service_health = "degraded"
        detail = "contracts valid but runtime checks degraded"
    else:
        state = "failed"
        service_health = "failed"
        detail = "environment prerequisites incomplete"
    checks = (
        ("docker_installed", "pass" if docker_installed else "warn"),
        ("docker_daemon_running", "pass" if docker_daemon else "warn"),
        ("compose_available", "pass" if compose_available else "warn"),
        ("static_health", "pass" if static_ok else "warn"),
        ("runtime_health", "pass" if runtime_ok else "warn"),
    )
    return (
        DeploymentHealthState(
            state=state,
            service_health=service_health,
            environment_ready=environment_ready,
            docker_installed=docker_installed,
            docker_daemon_running=docker_daemon,
            compose_available=compose_available,
            detail=detail,
            checks=checks,
        ),
        (perf_counter() - started) * 1000.0,
    )
