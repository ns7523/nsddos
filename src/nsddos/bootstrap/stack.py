"""Compose backend detection and stack control."""

from __future__ import annotations

import subprocess
from pathlib import Path
from shutil import which

from nsddos.bootstrap.service_monitor import parse_compose_ps_output
from nsddos.bootstrap.state import ComposeBackend, StartupServiceStatus
from nsddos.constants import COMPOSE_FILE


def detect_compose_backend() -> ComposeBackend | None:
    """Detect compose backend preference."""

    if which("docker") is not None:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0:
            return ComposeBackend(name="docker-compose-v2", command=("docker", "compose"))
    if which("docker-compose") is not None:
        return ComposeBackend(name="docker-compose-v1", command=("docker-compose",))
    return None


def compose_command(
    backend: ComposeBackend,
    args: tuple[str, ...],
    compose_file: Path = COMPOSE_FILE,
) -> tuple[str, ...]:
    """Build full compose command."""

    return (*backend.command, "-f", str(compose_file), *args)


def run_compose_command(
    backend: ComposeBackend,
    args: tuple[str, ...],
    compose_file: Path = COMPOSE_FILE,
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
    compose_file: Path = COMPOSE_FILE,
) -> tuple[StartupServiceStatus, ...]:
    """List compose services."""

    result = run_compose_command(backend, ("ps", "--format", "json"), compose_file)
    if result.returncode != 0:
        return ()
    return parse_compose_ps_output(result.stdout.strip())


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
    compose_file: Path = COMPOSE_FILE,
) -> subprocess.CompletedProcess[str]:
    """Start compose stack."""

    args = ("up", "-d", "--build") if rebuild else ("up", "-d",)
    return run_compose_command(backend, args, compose_file)
