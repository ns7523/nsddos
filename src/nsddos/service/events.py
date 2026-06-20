"""Typed service events."""

from __future__ import annotations

import json
from typing import Any

import nsddos.service.persistence as persistence
from nsddos.service.models import ServiceEvent


def append_service_event(event: ServiceEvent) -> None:
    persistence.ensure_service_dirs()
    with persistence.EVENTS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.to_dict()) + "\n")


def load_service_events() -> list[dict[str, Any]]:
    if not persistence.EVENTS_PATH.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in persistence.EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    rows.sort(key=lambda item: (int(item.get("sequence", 0)), item.get("timestamp", "")))
    return rows
