"""Deterministic backpressure decisions."""

from __future__ import annotations

from nsddos.runtime.streaming.contracts import StreamBackpressureState, StreamBufferState, StreamQueueState


def evaluate_backpressure(
    queue_state: StreamQueueState,
    *,
    max_queue_depth: int,
    buffer_state: StreamBufferState,
) -> StreamBackpressureState:
    queue_ratio = queue_state.queue_depth / max(max_queue_depth, 1)
    buffer_pressure = len(buffer_state.events) / max(buffer_state.max_size or 1, 1)
    state = "normal"
    throttled = False
    if queue_ratio >= 1.0 or buffer_state.overflowed:
        state = "overflow"
        throttled = True
    elif queue_ratio >= 0.8 or buffer_pressure >= 0.8:
        state = "throttled"
        throttled = True
    elif queue_ratio >= 0.5 or buffer_pressure >= 0.5:
        state = "congested"
    return StreamBackpressureState(
        state=state,
        queue_depth=queue_state.queue_depth,
        buffer_pressure=buffer_pressure,
        dropped_events=buffer_state.dropped_events,
        throttled=throttled,
    )
