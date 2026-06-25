"""Service query adapter."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.query.models import RuntimeQuery
from nsddos.service.diagnostics import collect_service_diagnostics
from nsddos.service.persistence import load_service_state
from nsddos.service.sessions import list_sessions


def query_service(config: dict[str, Any], query: RuntimeQuery) -> dict[str, Any]:
    state = load_service_state()
    sessions = list_sessions()
    diagnostics = collect_service_diagnostics()
    items = [
        {
            "id": "service-state",
            "kind": "service",
            "state": state.state,
            "owner": state.owner,
            "replay_safe": state.replay_safe,
        },
        {
            "id": "service-sync",
            "kind": "synchronization",
            **(state.synchronization or {}),
        },
    ]
    items.extend(
        {
            "id": item.session_id,
            "kind": "session",
            "owner": item.owner,
            "state": item.state,
            "lifecycle": item.lifecycle,
            "replay_cursor": item.replay.cursor,
            "sync_state": item.synchronization.sync_state,
        }
        for item in sessions
    )
    items.append(
        {
            "id": "service-diagnostics",
            "kind": "diagnostics",
            "session_count": diagnostics.get("session_count", 0),
            "heartbeat_count": diagnostics.get("heartbeat_count", 0),
        }
    )
    return {"items": items, "diagnostics": diagnostics}
