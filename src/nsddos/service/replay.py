"""Replay-safe service reconstruction."""

from __future__ import annotations

from nsddos.service.events import load_service_events


def replay_service_events(from_sequence: int = 0) -> dict:
    events = [item for item in load_service_events() if int(item.get("sequence", 0)) >= from_sequence]
    return {
        "event_count": len(events),
        "from_sequence": from_sequence,
        "latest_sequence": max((int(item.get("sequence", 0)) for item in events), default=0),
        "events": events,
    }
