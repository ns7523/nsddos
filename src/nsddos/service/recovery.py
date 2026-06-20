"""Service recovery."""

from __future__ import annotations

from nsddos.service.events import load_service_events
from nsddos.service.persistence import load_service_state, load_sessions


def recover_service_state() -> dict:
    state = load_service_state()
    sessions = load_sessions()
    events = load_service_events()
    recovered = {
        "service": state.to_dict(),
        "sessions": [item.to_dict() for item in sessions],
        "events": len(events),
        "replay_safe": state.replay_safe,
    }
    if state.state == "running" and not any(item.state == "active" for item in sessions):
        recovered["degraded"] = True
        recovered["reason"] = "running service without active session"
    return recovered
