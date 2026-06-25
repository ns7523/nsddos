"""Service lifecycle state transitions."""

from __future__ import annotations

from datetime import datetime, timezone

from nsddos.service.models import ServiceState


def mark_started(
    state: ServiceState, owner: str, session_id: str, lock_owner: str
) -> ServiceState:
    timestamp = datetime.now(timezone.utc).isoformat()
    state.state = "running"
    state.owner = owner
    state.active_session_id = session_id
    state.startup_count += 1
    state.started_at = state.started_at or timestamp
    state.updated_at = timestamp
    state.lock_owner = lock_owner
    state.last_error = None
    return state


def mark_stopped(state: ServiceState) -> ServiceState:
    state.state = "stopped"
    state.active_session_id = None
    state.owner = ""
    state.lock_owner = None
    state.updated_at = datetime.now(timezone.utc).isoformat()
    return state


def mark_degraded(state: ServiceState, reason: str) -> ServiceState:
    state.degraded = True
    state.last_error = reason
    state.updated_at = datetime.now(timezone.utc).isoformat()
    return state
