"""Dashboard stream aggregation."""

from __future__ import annotations

from nsddos.dashboard.contracts import DashboardSourceBundle, StreamState


def build_stream_state(sources: DashboardSourceBundle) -> StreamState:
    """Aggregate stream metrics."""
    stream = sources.streaming
    diagnostics = stream.get("diagnostics", {})
    queue_state = stream.get("queue_state", {})
    session = stream.get("session", {})
    return StreamState(
        active_streams=1 if session.get("session_id") else 0,
        stream_latency_ms=float(diagnostics.get("queue_latency_ms", 0.0)),
        event_throughput=float(
            stream.get("throughput", diagnostics.get("processing_throughput", 0.0))
        ),
        queue_depth=int(queue_state.get("queue_depth", 0)),
        dropped_events=int(
            stream.get("dropped_events", diagnostics.get("dropped_event_count", 0))
        ),
    )
