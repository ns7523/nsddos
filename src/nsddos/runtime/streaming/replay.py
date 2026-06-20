"""Streaming replay helpers."""

from __future__ import annotations

from nsddos.runtime.streaming.contracts import StreamCheckpoint, StreamEvent


def replay_from_checkpoint(checkpoint: StreamCheckpoint) -> tuple[StreamEvent, ...]:
    return checkpoint.buffer_state.events or checkpoint.queue_state.events
