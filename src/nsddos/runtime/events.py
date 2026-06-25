"""Runtime event logging and timeline reconstruction."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nsddos.config import ensure_runtime_directories
from nsddos.constants import EVENTS_PATH
from nsddos.runtime.models import RuntimeTimelineEvent


def emit_runtime_event(
    event_type: str,
    status: str,
    message: str,
    details: dict[str, Any] | None = None,
    event_path: Path = EVENTS_PATH,
) -> Path:
    """Append JSONL runtime event."""
    ensure_runtime_directories()
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "status": status,
        "message": message,
        "details": details or {},
    }
    with event_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload) + "\n")
    return event_path


def load_runtime_events(event_path: Path = EVENTS_PATH) -> list[dict[str, Any]]:
    """Load raw runtime events from JSONL."""
    if not event_path.exists():
        return []
    events: list[dict[str, Any]] = []
    with event_path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    events.sort(key=lambda item: item.get("timestamp", ""))
    return events


def build_runtime_timeline(
    event_path: Path = EVENTS_PATH,
) -> list[RuntimeTimelineEvent]:
    """Reconstruct ordered runtime timeline from persisted events."""
    raw_events = load_runtime_events(event_path)
    timeline: list[RuntimeTimelineEvent] = []
    previous_timestamp: datetime | None = None

    for event in raw_events:
        current_timestamp = None
        try:
            current_timestamp = datetime.fromisoformat(
                str(event.get("timestamp", "")).replace("Z", "+00:00")
            )
        except ValueError:
            current_timestamp = None

        duration_ms = None
        if previous_timestamp and current_timestamp:
            duration_ms = max(
                0.0,
                (current_timestamp - previous_timestamp).total_seconds() * 1000,
            )

        timeline.append(
            RuntimeTimelineEvent(
                timestamp=str(event.get("timestamp", "")),
                event_type=str(event.get("event_type", "")),
                status=str(event.get("status", "")),
                message=str(event.get("message", "")),
                details=event.get("details", {}) or {},
                duration_ms=duration_ms,
            )
        )
        previous_timestamp = current_timestamp

    return timeline
