"""Streaming validation."""

from __future__ import annotations

from datetime import datetime, timezone

from nsddos.runtime.streaming.contracts import (
    BACKPRESSURE_STATES,
    STREAM_SOURCE_TYPES,
    STREAM_WINDOW_KINDS,
    StreamCheckpoint,
    StreamEvent,
    StreamingEvaluation,
)


def validate_stream_events(events: tuple[StreamEvent, ...]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    last_sequence = -1
    now = datetime.now(timezone.utc)
    ordered = tuple(
        sorted(
            events,
            key=lambda item: (
                item.timestamp.isoformat(),
                item.sequence_number,
                item.event_id,
            ),
        )
    )
    for item in ordered:
        if item.source_type not in STREAM_SOURCE_TYPES:
            errors.append("invalid_source_type")
        if not item.event_id:
            errors.append("missing_event_id")
        if item.event_id in seen_ids:
            errors.append("duplicate_event_id")
        seen_ids.add(item.event_id)
        if item.sequence_number <= last_sequence:
            errors.append("invalid_sequence_ordering")
        last_sequence = item.sequence_number
        if item.timestamp > now.replace(year=2100):
            errors.append("invalid_timestamp")
        if item.packet_rate < 0 or item.byte_rate < 0 or item.connection_rate < 0:
            errors.append("malformed_event_packet")
        if item.freshness_state == "expired":
            errors.append("stale_event_packet")
    return sorted(set(errors))


def validate_checkpoint(checkpoint: StreamCheckpoint) -> list[str]:
    errors: list[str] = []
    if not checkpoint.checkpoint_id:
        errors.append("checkpoint_corruption")
    if checkpoint.event_offset < 0 or checkpoint.sequence_number < 0:
        errors.append("invalid_sequence_ordering")
    if checkpoint.queue_state.queue_depth != len(checkpoint.queue_state.events):
        errors.append("queue_corruption")
    if checkpoint.buffer_state.max_size < len(checkpoint.buffer_state.events):
        errors.append("buffer_corruption")
    return sorted(set(errors))


def validate_streaming_evaluation(evaluation: StreamingEvaluation) -> list[str]:
    errors = validate_stream_events(evaluation.source_events)
    errors.extend(validate_checkpoint(evaluation.checkpoint))
    if evaluation.window_state.window_kind not in STREAM_WINDOW_KINDS:
        errors.append("invalid_window_kind")
    if evaluation.backpressure.state not in BACKPRESSURE_STATES:
        errors.append("invalid_backpressure_state")
    if evaluation.active_events < 0 or evaluation.throughput < 0:
        errors.append("invalid_stream_metrics")
    return sorted(set(errors))
