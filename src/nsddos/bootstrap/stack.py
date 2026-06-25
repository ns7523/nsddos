"""Compose backend detection and stack control."""

from __future__ import annotations

import subprocess
from pathlib import Path

from nsddos.bootstrap.state import ComposeBackend, StartupServiceStatus
from nsddos.constants import get_compose_file
from nsddos.compose import compose_backend_name, resolve_compose_command
from nsddos.docker_manager import DockerManager


def detect_compose_backend() -> ComposeBackend | None:
    """Detect compose backend preference."""

    command = resolve_compose_command()
    if command is None:
        return None
    return ComposeBackend(name=compose_backend_name(command), command=command)


def compose_command(
    backend: ComposeBackend,
    args: tuple[str, ...],
    compose_file: Path | None = None,
) -> tuple[str, ...]:
    """Build full compose command."""

    target = compose_file or get_compose_file()
    return (*backend.command, "-f", str(target), *args)


def run_compose_command(
    backend: ComposeBackend,
    args: tuple[str, ...],
    compose_file: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run compose command."""

    return subprocess.run(
        compose_command(backend, args, compose_file),
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )


def list_stack_services(
    backend: ComposeBackend,
    compose_file: Path | None = None,
) -> tuple[StartupServiceStatus, ...]:
    """List compose services."""
    _ = backend
    services = DockerManager(compose_file=compose_file or get_compose_file()).get_service_states()
    return tuple(
        StartupServiceStatus(
            service_name=service.name,
            container_name=service.name if service.name.startswith("nsddos-") else f"nsddos-{service.name}",
            state=service.status,
            health=service.detail or service.status,
            healthy=service.healthy,
            container_id=service.container_id,
        )
        for service in services
    )


def stack_is_healthy(
    services: tuple[StartupServiceStatus, ...],
    required_container_names: tuple[str, ...],
) -> bool:
    """Return whether required services are healthy."""

    by_name = {service.container_name: service for service in services}
    return all(name in by_name and by_name[name].healthy for name in required_container_names)


def stack_has_required_services(
    services: tuple[StartupServiceStatus, ...],
    required_container_names: tuple[str, ...],
) -> bool:
    """Return whether all required services exist."""

    available = {service.container_name for service in services}
    return all(name in available for name in required_container_names)


def start_stack(
    backend: ComposeBackend,
    *,
    rebuild: bool,
    compose_file: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Start compose stack."""

    args = ("up", "-d", "--build") if rebuild else ("up", "-d",)
    return run_compose_command(backend, args, compose_file)
