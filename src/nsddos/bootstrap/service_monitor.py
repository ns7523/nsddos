"""Compose service status normalization."""

from __future__ import annotations

from nsddos.docker_manager import DockerManager
from nsddos.bootstrap.state import StartupServiceStatus


def parse_compose_ps_output(raw: str) -> tuple[StartupServiceStatus, ...]:
    """Parse compose ps JSON output across backends."""
    return tuple(
        StartupServiceStatus(
            service_name=service.name,
            container_name=service.name,
            state=service.status,
            health=service.detail or service.status,
            healthy=service.healthy,
            container_id=service.container_id,
        )
        for service in (
            DockerManager._normalize_service(item)
            for item in DockerManager._parse_compose_ps_output(raw)
        )
    )
