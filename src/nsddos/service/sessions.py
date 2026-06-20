"""Service runtime sessions."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from nsddos.service.models import RuntimeSession
from nsddos.service.persistence import load_sessions, save_sessions


def create_session(owner: str, metadata: dict | None = None) -> RuntimeSession:
    session = RuntimeSession(
        session_id=f"session-{uuid4()}",
        owner=owner,
        state="active",
        lifecycle="startup",
        metadata=metadata or {},
    )
    sessions = load_sessions()
    sessions.append(session)
    save_sessions(sessions)
    return session


def list_sessions() -> list[RuntimeSession]:
    return load_sessions()


def update_session(session: RuntimeSession) -> RuntimeSession:
    sessions = load_sessions()
    next_sessions: list[RuntimeSession] = []
    for item in sessions:
        if item.session_id == session.session_id:
            session.updated_at = datetime.now(timezone.utc).isoformat()
            next_sessions.append(session)
        else:
            next_sessions.append(item)
    save_sessions(next_sessions)
    return session


def stop_session(session_id: str, state: str = "stopped") -> RuntimeSession | None:
    sessions = load_sessions()
    target: RuntimeSession | None = None
    for item in sessions:
        if item.session_id == session_id:
            item.state = state
            item.lifecycle = "shutdown"
            item.updated_at = datetime.now(timezone.utc).isoformat()
            target = item
            break
    save_sessions(sessions)
    return target
