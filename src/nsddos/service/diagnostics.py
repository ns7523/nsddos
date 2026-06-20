"""Service diagnostics."""

from __future__ import annotations

from nsddos.service.persistence import load_heartbeat, load_service_state, load_sessions, load_synchronization
from nsddos.service.replay import replay_service_events
from nsddos.runtime.streaming import latest_checkpoint, latest_session, latest_streaming_evaluation


def collect_service_diagnostics() -> dict:
    state = load_service_state()
    sessions = load_sessions()
    heartbeat = load_heartbeat()
    synchronization = load_synchronization()
    replay = replay_service_events()
    return {
        "service_state": state.to_dict(),
        "session_count": len(sessions),
        "active_sessions": [item.to_dict() for item in sessions if item.state in {"active", "synchronizing", "replaying"}],
        "heartbeat_count": len(heartbeat.get("heartbeats", [])),
        "last_heartbeat": (heartbeat.get("heartbeats", []) or [{}])[-1],
        "synchronization": synchronization.get("latest", {}),
        "replay": {
            "event_count": replay.get("event_count", 0),
            "latest_sequence": replay.get("latest_sequence", 0),
        },
        "streaming": {
            "latest_session": latest_session(),
            "latest_checkpoint": latest_checkpoint(),
            "latest_evaluation": latest_streaming_evaluation(),
        },
    }
