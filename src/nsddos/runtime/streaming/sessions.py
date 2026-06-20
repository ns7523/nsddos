"""Streaming session persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from io import TextIOWrapper

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.domain.identifiers import deterministic_id
from nsddos.runtime.persistence import atomic_write_json, read_json_checked
from nsddos.runtime.streaming.contracts import StreamSession

STREAMING_DIR = RUNTIME_DIR / "streaming"
SESSION_DIR = STREAMING_DIR / "sessions"


def build_session(
    source_mode: str,
    *,
    session_id: str | None = None,
    processed_events_count: int = 0,
    last_checkpoint_id: str = "",
    last_sequence_number: int = 0,
    session_state: str = "active",
    session_start: datetime | None = None,
) -> StreamSession:
    created = session_start or datetime.now(timezone.utc)
    resolved_session_id = session_id or deterministic_id("stream-session", f"{source_mode}:{created.isoformat()}")
    return StreamSession(
        session_id=resolved_session_id,
        source_mode=source_mode,
        session_start=created,
        session_state=session_state,
        processed_events_count=processed_events_count,
        last_checkpoint_id=last_checkpoint_id,
        last_sequence_number=last_sequence_number,
    )


def persist_session(session: StreamSession, *, lock_scope: TextIOWrapper | None = None) -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    payload = session.to_dict()
    stamp = session.session_start.strftime("%Y%m%dT%H%M%S%fZ")
    atomic_write_json(SESSION_DIR / f"session-{stamp}.json", payload, lock_scope=lock_scope)
    atomic_write_json(SESSION_DIR / "latest.json", payload, lock_scope=lock_scope)


def latest_session() -> dict[str, object]:
    path = SESSION_DIR / "latest.json"
    if not path.exists():
        return {}
    return read_json_checked(path)
