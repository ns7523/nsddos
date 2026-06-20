"""Streaming diagnostics."""

from __future__ import annotations

from nsddos.runtime.streaming.contracts import (
    StreamBackpressureState,
    StreamBufferState,
    StreamCheckpoint,
    StreamQueueState,
    StreamSession,
    StreamingDiagnostics,
)


def build_streaming_diagnostics(
    session: StreamSession,
    queue_state: StreamQueueState,
    buffer_state: StreamBufferState,
    backpressure: StreamBackpressureState,
    checkpoint: StreamCheckpoint,
    *,
    throughput: float,
) -> StreamingDiagnostics:
    health = "healthy"
    if backpressure.state in {"congested", "throttled"}:
        health = "degraded"
    if backpressure.state == "overflow":
        health = "overflow"
    checkpoint_lag = max(0, session.processed_events_count - checkpoint.event_offset)
    return StreamingDiagnostics(
        queue_latency_ms=float(queue_state.queue_depth * 5),
        processing_throughput=throughput,
        dropped_event_count=buffer_state.dropped_events,
        buffer_pressure=backpressure.buffer_pressure,
        session_health=health,
        checkpoint_lag=checkpoint_lag,
    )
