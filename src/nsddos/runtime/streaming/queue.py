"""Deterministic stream queue."""

from __future__ import annotations

from nsddos.runtime.streaming.contracts import StreamEvent, StreamQueueState


def order_events(events: tuple[StreamEvent, ...]) -> tuple[StreamEvent, ...]:
    return tuple(
        sorted(
            events,
            key=lambda item: (
                item.timestamp.isoformat(),
                item.sequence_number,
                item.event_id,
            ),
        )
    )


def build_queue_state(
    events: tuple[StreamEvent, ...],
    *,
    dequeued_count: int = 0,
) -> StreamQueueState:
    ordered = order_events(events)
    return StreamQueueState(
        events=ordered,
        queue_depth=len(ordered),
        enqueued_count=len(ordered),
        dequeued_count=dequeued_count,
    )


def dequeue_batch(
    queue_state: StreamQueueState, batch_size: int
) -> tuple[tuple[StreamEvent, ...], StreamQueueState]:
    batch = queue_state.events[:batch_size]
    remaining = queue_state.events[batch_size:]
    return (
        batch,
        StreamQueueState(
            events=remaining,
            queue_depth=len(remaining),
            enqueued_count=queue_state.enqueued_count,
            dequeued_count=queue_state.dequeued_count + len(batch),
        ),
    )
