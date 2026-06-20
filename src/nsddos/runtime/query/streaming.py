"""Streaming query adapters."""

from __future__ import annotations

from nsddos.runtime.streaming import latest_checkpoint, latest_streaming_evaluation, process_stream_events


def query_stream_status(config: dict, query) -> dict[str, object]:
    payload = latest_streaming_evaluation()
    if not payload:
        payload = process_stream_events(config).to_dict()
    session = payload.get("session", {})
    diagnostics = payload.get("diagnostics", {})
    return {
        "items": [
            {
                "id": "stream-status",
                "type": "stream_status",
                "session_id": session.get("session_id", ""),
                "active_events": payload.get("active_events", 0),
                "queue_depth": payload.get("queue_state", {}).get("queue_depth", 0),
                "dropped_events": payload.get("dropped_events", 0),
                "throughput": payload.get("throughput", 0.0),
                "stream_state": payload.get("stream_state", "unknown"),
                "timestamp": payload.get("timestamp", ""),
                "session_health": diagnostics.get("session_health", "unknown"),
            }
        ]
    }


def query_stream_checkpoint(config: dict, query) -> dict[str, object]:
    checkpoint = latest_checkpoint()
    if not checkpoint:
        checkpoint = process_stream_events(config).checkpoint.to_dict()
    return {
        "items": [
            {
                "id": "stream-checkpoint",
                "type": "stream_checkpoint",
                "session_id": checkpoint.get("session_id", ""),
                "checkpoint_id": checkpoint.get("checkpoint_id", ""),
                "event_offset": checkpoint.get("event_offset", 0),
                "sequence_number": checkpoint.get("sequence_number", 0),
                "queue_depth": checkpoint.get("queue_state", {}).get("queue_depth", 0),
                "timestamp": checkpoint.get("timestamp", ""),
            }
        ]
    }


def query_stream_diagnostics(config: dict, query) -> dict[str, object]:
    payload = latest_streaming_evaluation()
    if not payload:
        payload = process_stream_events(config).to_dict()
    diagnostics = payload.get("diagnostics", {})
    return {
        "items": [
            {
                "id": "stream-diagnostics",
                "type": "stream_diagnostics",
                "queue_latency_ms": diagnostics.get("queue_latency_ms", 0.0),
                "processing_throughput": diagnostics.get("processing_throughput", 0.0),
                "dropped_event_count": diagnostics.get("dropped_event_count", 0),
                "buffer_pressure": diagnostics.get("buffer_pressure", 0.0),
                "session_health": diagnostics.get("session_health", "unknown"),
                "checkpoint_lag": diagnostics.get("checkpoint_lag", 0),
                "timestamp": payload.get("timestamp", ""),
            }
        ]
    }
