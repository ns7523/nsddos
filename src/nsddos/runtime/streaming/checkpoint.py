"""Streaming checkpoint persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from io import TextIOWrapper

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.domain.identifiers import deterministic_id
from nsddos.runtime.persistence import atomic_write_json, read_json_checked
from nsddos.runtime.streaming.contracts import StreamBufferState, StreamCheckpoint, StreamQueueState

STREAMING_DIR = RUNTIME_DIR / "streaming"
CHECKPOINT_DIR = STREAMING_DIR / "checkpoints"


def build_checkpoint(
    session_id: str,
    queue_state: StreamQueueState,
    buffer_state: StreamBufferState,
    *,
    event_offset: int,
    sequence_number: int,
    timestamp: datetime | None = None,
) -> StreamCheckpoint:
    created = timestamp or datetime.now(timezone.utc)
    checkpoint_id = deterministic_id("stream-checkpoint", f"{session_id}:{event_offset}:{sequence_number}:{created.isoformat()}")
    return StreamCheckpoint(
        checkpoint_id=checkpoint_id,
        session_id=session_id,
        event_offset=event_offset,
        queue_state=queue_state,
        buffer_state=buffer_state,
        sequence_number=sequence_number,
        timestamp=created,
    )


def persist_checkpoint(checkpoint: StreamCheckpoint, *, lock_scope: TextIOWrapper | None = None) -> None:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    payload = checkpoint.to_dict()
    stamp = checkpoint.timestamp.strftime("%Y%m%dT%H%M%S%fZ")
    atomic_write_json(CHECKPOINT_DIR / f"checkpoint-{stamp}.json", payload, lock_scope=lock_scope)
    atomic_write_json(CHECKPOINT_DIR / "latest.json", payload, lock_scope=lock_scope)


def latest_checkpoint() -> dict[str, object]:
    path = CHECKPOINT_DIR / "latest.json"
    if not path.exists():
        return {}
    return read_json_checked(path)
