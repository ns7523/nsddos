"""Timeline query adapter."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.events import build_runtime_timeline
from nsddos.runtime.query.models import RuntimeQuery
from nsddos.runtime.transitions import load_transition_history


def query_timeline(config: dict[str, Any], query: RuntimeQuery) -> dict[str, Any]:
    """Query runtime events and transitions."""
    events = [item.to_dict() for item in build_runtime_timeline()]
    transitions = load_transition_history()
    items = [
        {
            "id": f"event:{index}",
            "record_type": "event",
            "timestamp": item.get("timestamp", ""),
            "event_type": item.get("event_type", ""),
            "status": item.get("status", ""),
            "message": item.get("message", ""),
        }
        for index, item in enumerate(events)
    ]
    items.extend(
        {
            "id": str(item.get("id", f"transition:{index}")),
            "record_type": "transition",
            "timestamp": item.get("timestamp", ""),
            "event_type": item.get("event_type", item.get("kind", "")),
            "kind": item.get("kind", ""),
            "status": item.get("status", ""),
            "message": item.get("message", ""),
        }
        for index, item in enumerate(transitions)
    )
    return {"items": items, "transitions": transitions}
