"""Replay-safe stream buffer."""

from __future__ import annotations

from nsddos.runtime.streaming.contracts import StreamBufferState, StreamEvent


def build_buffer_state(
    events: tuple[StreamEvent, ...],
    *,
    max_size: int,
    overflow_policy: str,
) -> StreamBufferState:
    overflowed = len(events) > max_size
    dropped = max(0, len(events) - max_size)
    buffered = events
    if overflowed:
        if overflow_policy == "drop_oldest":
            buffered = events[-max_size:]
        else:
            buffered = events[:max_size]
    return StreamBufferState(
        events=buffered,
        max_size=max_size,
        dropped_events=dropped,
        overflowed=overflowed,
    )
