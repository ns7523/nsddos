"""Runtime execution replay from persisted events."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.domain.identifiers import replay_id
from nsddos.runtime.domain.replay import reconstruct_replay, validate_replay_compatibility
from nsddos.runtime.domain.serialization import to_canonical_dict
from nsddos.runtime.events import load_runtime_events


def replay_execution_history() -> dict[str, Any]:
    """Replay persisted pipeline events."""
    events = [
        event
        for event in load_runtime_events()
        if str(event.get("event_type", "")).startswith("pipeline.")
    ]
    phases = [
        {
            "replay_id": replay_id(str(event.get("event_type", "")), str(event.get("timestamp", "")), index),
            "timestamp": event.get("timestamp", ""),
            "event_type": event.get("event_type", ""),
            "status": event.get("status", ""),
            "message": event.get("message", ""),
            "details": event.get("details", {}),
        }
        for index, event in enumerate(events, start=1)
    ]
    typed_replay = reconstruct_replay(phases)
    replay_errors = validate_replay_compatibility(typed_replay)
    return {
        "event_count": len(events),
        "phases": phases,
        "failed": [item for item in phases if item["status"] == "failed"],
        "warnings": [item for item in phases if item["status"] == "warn"],
        "typed_replay": [to_canonical_dict(item) for item in typed_replay.events],
        "replay_contract_errors": replay_errors,
    }
