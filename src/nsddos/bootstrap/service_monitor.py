"""Compose service status normalization."""

from __future__ import annotations

import json
from typing import Any

from nsddos.bootstrap.state import StartupServiceStatus


def parse_compose_ps_output(raw: str) -> tuple[StartupServiceStatus, ...]:
    """Parse compose ps JSON output across backends."""

    if not raw:
        return ()
    parsed: list[dict[str, Any]] = []
    try:
        payload = json.loads(raw)
        if isinstance(payload, list):
            parsed = [item for item in payload if isinstance(item, dict)]
        elif isinstance(payload, dict):
            parsed = [payload]
    except json.JSONDecodeError:
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                parsed.append(payload)

    services: list[StartupServiceStatus] = []
    for item in parsed:
        state = str(item.get("State", item.get("state", "unknown")))
        health = str(item.get("Health", item.get("health", state)))
        container_name = str(item.get("Name", item.get("name", "")))
        service_name = str(item.get("Service", item.get("service", container_name)))
        healthy = state.lower() == "running" and health.lower() not in {"unhealthy", "exited", "dead"}
        services.append(
            StartupServiceStatus(
                service_name=service_name,
                container_name=container_name,
                state=state,
                health=health,
                healthy=healthy,
                container_id=str(item.get("ID", item.get("Id", item.get("id", "")))) or None,
            )
        )
    return tuple(services)
