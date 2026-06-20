"""Streaming pipeline metadata."""

from __future__ import annotations

from nsddos.runtime.streaming.registry import default_streaming_registry


def describe_streaming_pipeline() -> dict[str, object]:
    registry = default_streaming_registry()
    return {
        "processors": [
            {"name": item.name, "handler_name": item.handler_name}
            for item in registry.processors.values()
        ],
        "active_session_lookup": "runtime.streaming.sessions.latest_session",
        "pipeline_lookup": registry.pipeline_lookup,
    }
