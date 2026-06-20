"""Deterministic heartbeat tracking."""

from __future__ import annotations

from uuid import uuid4

from nsddos.service.models import ServiceHeartbeat, ServiceState
from nsddos.service.persistence import load_heartbeat, save_heartbeat
from nsddos.service.sessions import list_sessions


def emit_heartbeat(state: ServiceState, synchronization_state: str, replay_state: str, detail: str = "") -> ServiceHeartbeat:
    sessions = list_sessions()
    heartbeat = ServiceHeartbeat(
        heartbeat_id=f"hb-{uuid4()}",
        service_state=state.state,
        session_count=len([item for item in sessions if item.state in {"active", "synchronizing", "replaying"}]),
        synchronization_state=synchronization_state,
        replay_state=replay_state,
        detail=detail,
    )
    payload = load_heartbeat()
    history = payload.get("heartbeats", [])
    history.append(heartbeat.to_dict())
    save_heartbeat({"heartbeats": history[-200:]})
    return heartbeat
