"""Deterministic streaming engine."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.persistence import (
    atomic_write_json,
    locked_persistence_scope,
    read_json_checked,
)
from nsddos.runtime.streaming.aggregation import aggregate_events
from nsddos.runtime.streaming.backpressure import evaluate_backpressure
from nsddos.runtime.streaming.buffer import build_buffer_state
from nsddos.runtime.streaming.checkpoint import build_checkpoint, persist_checkpoint
from nsddos.runtime.streaming.contracts import StreamEvent, StreamingEvaluation
from nsddos.runtime.streaming.diagnostics import build_streaming_diagnostics
from nsddos.runtime.streaming.dispatcher import (
    dispatch_detection,
    dispatch_mitigation,
    dispatch_ml,
    dispatch_policy,
)
from nsddos.runtime.streaming.events import resolve_source_events
from nsddos.runtime.streaming.queue import build_queue_state, dequeue_batch
from nsddos.runtime.streaming.recovery import (
    restore_checkpoint,
    restore_session,
    validate_recovery_state,
)
from nsddos.runtime.streaming.scheduler import resolve_batch_size
from nsddos.runtime.streaming.sessions import build_session, persist_session
from nsddos.runtime.streaming.validation import (
    validate_stream_events,
    validate_streaming_evaluation,
)
from nsddos.runtime.streaming.windowing import build_window_state

STREAMING_DIR = RUNTIME_DIR / "streaming"


def _settings(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("runtime", {}).get("streaming", {})


def _persist_evaluation(evaluation: StreamingEvaluation) -> None:
    STREAMING_DIR.mkdir(parents=True, exist_ok=True)
    payload = evaluation.to_dict()
    stamp = evaluation.timestamp.strftime("%Y%m%dT%H%M%S%fZ")
    with locked_persistence_scope(STREAMING_DIR) as lock_scope:
        atomic_write_json(
            STREAMING_DIR / f"streaming-{stamp}.json", payload, lock_scope=lock_scope
        )
        atomic_write_json(STREAMING_DIR / "latest.json", payload, lock_scope=lock_scope)


def latest_streaming_evaluation() -> dict[str, Any]:
    path = STREAMING_DIR / "latest.json"
    if not path.exists():
        return {}
    return read_json_checked(path)


def process_stream_events(
    config: dict[str, Any],
    session_id: str | None = None,
    events: tuple[StreamEvent, ...] | None = None,
) -> StreamingEvaluation:
    settings = _settings(config)
    source_mode, source_events = (
        resolve_source_events(config) if events is None else ("manual", events)
    )
    event_errors = validate_stream_events(source_events)
    if event_errors:
        raise ValueError(f"stream events invalid: {','.join(event_errors)}")
    restored_checkpoint = restore_checkpoint()
    restored_session = restore_session()
    recovery_errors = validate_recovery_state(restored_checkpoint, restored_session)
    if recovery_errors:
        raise ValueError(f"stream recovery invalid: {','.join(recovery_errors)}")
    queue_state = build_queue_state(source_events)
    batch_size = resolve_batch_size(config)
    batch, remaining_queue = dequeue_batch(queue_state, batch_size)
    buffer_state = build_buffer_state(
        batch,
        max_size=int(settings.get("max_buffer_size", 256)),
        overflow_policy=str(settings.get("overflow_policy", "drop_oldest")),
    )
    backpressure = evaluate_backpressure(
        queue_state,
        max_queue_depth=int(settings.get("max_queue_depth", 1024)),
        buffer_state=buffer_state,
    )
    window_state = build_window_state(
        buffer_state.events,
        window_kind=str(settings.get("window_kind", "sliding")),
        window_seconds=int(settings.get("window_seconds", 10)),
    )
    aggregation = aggregate_events(window_state)
    detection, telemetry = dispatch_detection(config, aggregation, buffer_state.events)
    ml = dispatch_ml(config, detection, telemetry)
    policy = dispatch_policy(config, detection, ml, telemetry)
    mitigation = dispatch_mitigation(config, detection, policy, telemetry)
    timestamp = datetime.now(timezone.utc)
    session = build_session(
        source_mode=source_mode,
        session_id=session_id
        or (restored_session.session_id if restored_session is not None else None),
        processed_events_count=len(buffer_state.events),
        last_sequence_number=(
            buffer_state.events[-1].sequence_number if buffer_state.events else 0
        ),
        session_state="throttled" if backpressure.throttled else "active",
        session_start=(
            restored_session.session_start
            if restored_session is not None and session_id is None
            else None
        ),
    )
    checkpoint = build_checkpoint(
        session.session_id,
        remaining_queue,
        buffer_state,
        event_offset=len(buffer_state.events),
        sequence_number=session.last_sequence_number,
        timestamp=timestamp,
    )
    session = build_session(
        source_mode=source_mode,
        session_id=session.session_id,
        processed_events_count=len(buffer_state.events),
        last_checkpoint_id=checkpoint.checkpoint_id,
        last_sequence_number=session.last_sequence_number,
        session_state="throttled" if backpressure.throttled else "active",
        session_start=session.session_start,
    )
    throughput = float(len(buffer_state.events)) / max(
        float(settings.get("window_seconds", 10)), 1.0
    )
    diagnostics = build_streaming_diagnostics(
        session,
        remaining_queue,
        buffer_state,
        backpressure,
        checkpoint,
        throughput=throughput,
    )
    evaluation = StreamingEvaluation(
        session=session,
        queue_state=remaining_queue,
        buffer_state=buffer_state,
        window_state=window_state,
        aggregation=aggregation,
        backpressure=backpressure,
        checkpoint=checkpoint,
        diagnostics=diagnostics,
        stream_state=session.session_state,
        active_events=len(buffer_state.events),
        dropped_events=buffer_state.dropped_events,
        throughput=throughput,
        timestamp=timestamp,
        detection_payload=detection.to_dict(),
        ml_payload=ml.to_dict(),
        policy_payload=policy.to_dict(),
        mitigation_payload=mitigation.to_dict(),
        source_events=source_events,
        created_at=timestamp.isoformat(),
    )
    evaluation_errors = validate_streaming_evaluation(evaluation)
    if evaluation_errors:
        raise ValueError(f"stream evaluation invalid: {','.join(evaluation_errors)}")
    with locked_persistence_scope(STREAMING_DIR / "checkpoints") as checkpoint_lock:
        persist_checkpoint(checkpoint, lock_scope=checkpoint_lock)
    with locked_persistence_scope(STREAMING_DIR / "sessions") as session_lock:
        persist_session(session, lock_scope=session_lock)
    _persist_evaluation(evaluation)
    return evaluation
