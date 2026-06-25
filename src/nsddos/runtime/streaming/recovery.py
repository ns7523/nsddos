"""Streaming recovery logic."""

from __future__ import annotations

from datetime import datetime

from nsddos.runtime.streaming.checkpoint import latest_checkpoint
from nsddos.runtime.streaming.contracts import (
    StreamBufferState,
    StreamCheckpoint,
    StreamEvent,
    StreamQueueState,
    StreamSession,
)
from nsddos.runtime.streaming.sessions import latest_session


def _event_from_dict(payload: dict[str, object]) -> StreamEvent:
    return StreamEvent(
        event_id=str(payload.get("event_id", "")),
        source_type=str(payload.get("source_type", "collection")),
        packet_rate=float(payload.get("packet_rate", 0.0)),
        byte_rate=float(payload.get("byte_rate", 0.0)),
        connection_rate=float(payload.get("connection_rate", 0.0)),
        protocol=str(payload.get("protocol", "")),
        source_ip=str(payload.get("source_ip", "")),
        destination_ip=str(payload.get("destination_ip", "")),
        timestamp=datetime.fromisoformat(
            str(payload.get("timestamp", "2100-01-01T00:00:00+00:00")).replace(
                "Z", "+00:00"
            )
        ),
        sequence_number=int(payload.get("sequence_number", 0)),
        freshness_state=str(payload.get("freshness_state", "valid")),
    )


def restore_checkpoint() -> StreamCheckpoint | None:
    payload = latest_checkpoint()
    if not payload:
        return None
    queue_events = tuple(
        _event_from_dict(item)
        for item in payload.get("queue_state", {}).get("events", [])
    )
    buffer_events = tuple(
        _event_from_dict(item)
        for item in payload.get("buffer_state", {}).get("events", [])
    )
    queue_state = StreamQueueState(
        events=queue_events,
        queue_depth=int(
            payload.get("queue_state", {}).get("queue_depth", len(queue_events))
        ),
        enqueued_count=int(
            payload.get("queue_state", {}).get("enqueued_count", len(queue_events))
        ),
        dequeued_count=int(payload.get("queue_state", {}).get("dequeued_count", 0)),
    )
    buffer_state = StreamBufferState(
        events=buffer_events,
        max_size=int(
            payload.get("buffer_state", {}).get("max_size", len(buffer_events))
        ),
        dropped_events=int(payload.get("buffer_state", {}).get("dropped_events", 0)),
        overflowed=bool(payload.get("buffer_state", {}).get("overflowed", False)),
    )
    return StreamCheckpoint(
        checkpoint_id=str(payload.get("checkpoint_id", "")),
        session_id=str(payload.get("session_id", "")),
        event_offset=int(payload.get("event_offset", 0)),
        queue_state=queue_state,
        buffer_state=buffer_state,
        sequence_number=int(payload.get("sequence_number", 0)),
        timestamp=datetime.fromisoformat(
            str(payload.get("timestamp", "2100-01-01T00:00:00+00:00")).replace(
                "Z", "+00:00"
            )
        ),
    )


def restore_session() -> StreamSession | None:
    payload = latest_session()
    if not payload:
        return None
    return StreamSession(
        session_id=str(payload.get("session_id", "")),
        source_mode=str(payload.get("source_mode", "collection")),
        session_start=datetime.fromisoformat(
            str(payload.get("session_start", "2100-01-01T00:00:00+00:00")).replace(
                "Z", "+00:00"
            )
        ),
        session_state=str(payload.get("session_state", "active")),
        processed_events_count=int(payload.get("processed_events_count", 0)),
        last_checkpoint_id=str(payload.get("last_checkpoint_id", "")),
        last_sequence_number=int(payload.get("last_sequence_number", 0)),
    )


def validate_recovery_state(
    checkpoint: StreamCheckpoint | None, session: StreamSession | None
) -> list[str]:
    if checkpoint is None and session is None:
        return []
    errors: list[str] = []
    if checkpoint is None or session is None:
        errors.append("incomplete_recovery_state")
        return errors
    if checkpoint.session_id != session.session_id:
        errors.append("session_checkpoint_mismatch")
    sequence_numbers = [item.sequence_number for item in checkpoint.queue_state.events]
    if sequence_numbers != sorted(sequence_numbers):
        errors.append("recovery_sequence_out_of_order")
    if checkpoint.sequence_number < session.last_sequence_number:
        errors.append("checkpoint_sequence_regressed")
    return errors
