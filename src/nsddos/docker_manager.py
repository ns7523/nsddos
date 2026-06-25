"""Docker Compose orchestration utilities."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from shutil import which
from typing import Any

import typer
from loguru import logger

from nsddos.config import build_runtime_state, load_runtime_state, write_runtime_state
from nsddos.compose import resolve_compose_command
from nsddos.constants import get_compose_file
from nsddos.runtime.models import ServiceState


class DockerManager:
    """Minimal Docker Compose runtime manager."""

    def __init__(self, compose_file: Path | None = None) -> None:
        self.compose_file = compose_file or get_compose_file()

    @staticmethod
    def is_docker_installed() -> bool:
        """Check Docker CLI availability."""
        return which("docker") is not None

    def is_daemon_running(self) -> bool:
        """Check Docker daemon availability."""
        if not self.is_docker_installed():
            return False
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0

    def compose_exists(self) -> bool:
        """Check compose file availability."""
        return self.compose_file.exists()

    @staticmethod
    def _compose_backend() -> list[str] | None:
        """Detect compose backend command."""
        command = resolve_compose_command()
        return list(command) if command is not None else None

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """Run subprocess for Docker operations."""
        backend = self._compose_backend()
        if backend is None:
            return subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="Compose backend unavailable"
            )
        command = [*backend, "-f", str(self.compose_file), *args]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logger.error(result.stderr.strip() or "Docker command failed")
        return result

    def _run_attached(self, args: list[str]) -> int:
        """Run compose command attached to terminal."""
        backend = self._compose_backend()
        if backend is None:
            return 1
        command = [*backend, "-f", str(self.compose_file), *args]
        process = subprocess.Popen(command)
        try:
            return process.wait()
        except KeyboardInterrupt:
            process.terminate()
            return 130

    def validate_environment(self) -> None:
        """Validate Docker execution prerequisites."""
        if not self.is_docker_installed():
            logger.error("Docker CLI not installed.")
            raise typer.Exit(code=1)
        if self._compose_backend() is None:
            logger.error("Docker Compose backend not available.")
            raise typer.Exit(code=1)
        if not self.is_daemon_running():
            logger.error("Docker daemon not running.")
            raise typer.Exit(code=1)
        if not self.compose_exists():
            logger.error("Compose file missing: {}", self.compose_file)
            raise typer.Exit(code=1)

    def start_stack(self) -> None:
        """Start compose stack."""
        self.start_services(["floodlight", "sflowrt", "detector"])

    def start_services(self, services: list[str]) -> None:
        """Start selected compose services."""
        self.validate_environment()
        result = self._run(["up", "-d", *services])
        if result.returncode != 0:
            logger.error("Failed to start lab stack.")
            raise typer.Exit(code=1)
        services = self.get_service_states()
        write_runtime_state(build_runtime_state(stack_running=True, services=services))

    def stop_stack(self) -> None:
        """Stop compose stack."""
        self.validate_environment()
        result = self._run(["down"])
        if result.returncode != 0:
            logger.error("Failed to stop lab stack.")
            raise typer.Exit(code=1)
        current = load_runtime_state()
        current.stack_running = False
        current.services = []
        current.topology_state = "stopped"
        current.topology_pid = None
        current.last_error = None
        current.updated_at = build_runtime_state(False).updated_at
        current.stopped_at = current.updated_at
        write_runtime_state(current)

    @staticmethod
    def _normalize_service(raw: dict[str, Any]) -> ServiceState:
        """Normalize `docker compose ps` entry."""
        state = str(raw.get("State", raw.get("state", "unknown")))
        health = str(raw.get("Health", raw.get("health", "")))
        healthy = state.lower() == "running" and health.lower() not in {"unhealthy"}
        return ServiceState(
            name=raw.get("Service", raw.get("Name", raw.get("service", "unknown"))),
            status=state,
            healthy=healthy,
            container_id=raw.get("ID", raw.get("Id", raw.get("id"))),
            provider="docker",
            endpoint=None,
            detail=health or state,
        )

    @staticmethod
    def _parse_compose_ps_output(raw: str) -> list[dict[str, Any]]:
        """Parse compose ps JSON output across compose variants."""
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                return [parsed]
        except json.JSONDecodeError:
            pass

        services: list[dict[str, Any]] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                services.append(parsed)
        return services

    @staticmethod
    def _parse_docker_ps_output(raw: str) -> list[ServiceState]:
        """Parse `docker ps --format` fallback output."""
        services: list[ServiceState] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line or "|" not in line:
                continue
            name, status = line.split("|", 1)
            name = name.strip()
            status = status.strip()
            if not name:
                continue
            services.append(
                ServiceState(
                    name=name,
                    status="running" if status.lower().startswith("up") else status,
                    healthy="(healthy)" in status.lower()
                    or ("up" in status.lower() and "(unhealthy)" not in status.lower()),
                    container_id=None,
                    provider="docker",
                    endpoint=None,
                    detail=status,
                )
            )
        return services

    @staticmethod
    def _service_aliases(name: str) -> set[str]:
        """Return service/container aliases."""

        aliases = {name}
        if name.startswith("nsddos-"):
            aliases.add(name.removeprefix("nsddos-"))
        else:
            aliases.add(f"nsddos-{name}")
        return aliases

    def _docker_ps_fallback(self) -> list[ServiceState]:
        """Return service states via `docker ps` when compose JSON unsupported."""
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}|{{.Status}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []
        return self._parse_docker_ps_output(result.stdout.strip())

    def get_service_states(self) -> list[ServiceState]:
        """Return normalized service states."""
        if not self.compose_exists():
            return []
        if not self.is_docker_installed() or not self.is_daemon_running():
            return []

        result = self._run(["ps", "--format", "json"])
        if result.returncode != 0:
            return self._docker_ps_fallback()

        parsed = self._parse_compose_ps_output(result.stdout.strip())
        if not parsed:
            return self._docker_ps_fallback()
        return [self._normalize_service(entry) for entry in parsed]

    def get_stack_service_states(
        self, required_names: tuple[str, ...]
    ) -> list[ServiceState]:
        """Return service states matched to required stack containers."""

        services = self.get_service_states()
        matched: list[ServiceState] = []
        for required_name in required_names:
            service = next(
                (
                    entry
                    for entry in services
                    if required_name in self._service_aliases(entry.name)
                ),
                None,
            )
            if service is None:
                matched.append(
                    ServiceState(
                        name=required_name,
                        status="missing",
                        healthy=False,
                        detail="missing",
                    )
                )
                continue
            matched.append(
                ServiceState(
                    name=required_name,
                    status=service.status,
                    healthy=service.healthy,
                    container_id=service.container_id,
                    provider=getattr(service, "provider", "docker"),
                    endpoint=getattr(service, "endpoint", None),
                    detail=getattr(service, "detail", service.status),
                )
            )
        return matched

    def stack_health(
        self, required_names: tuple[str, ...]
    ) -> tuple[bool, str, list[ServiceState]]:
        """Return normalized stack health tuple."""

        services = self.get_stack_service_states(required_names)
        detail = ", ".join(
            f"{service.name}:{service.detail or service.status}" for service in services
        )
        healthy = all(service.healthy for service in services)
        return healthy and bool(services), detail or "no containers", services

    def get_service_status(self) -> dict[str, Any]:
        """Return compose service status."""
        services = self.get_service_states()
        return {
            "running": any(service.status.lower() == "running" for service in services),
            "services": [service.to_dict() for service in services],
            "compose_file": str(self.compose_file),
        }

    def stream_logs(self, service: str | None = None) -> None:
        """Stream compose logs."""
        self.validate_environment()
        args = ["logs", "-f"]
        if service:
            args.append(service)
        result = self._run_attached(args)
        if result not in {0, 130}:
            logger.error("Failed to stream logs.")
            raise typer.Exit(code=1)
