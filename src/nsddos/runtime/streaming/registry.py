"""Streaming registry."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StreamingProcessor:
    name: str
    handler_name: str


@dataclass
class StreamingRegistry:
    processors: dict[str, StreamingProcessor] = field(default_factory=dict)
    pipeline_lookup: dict[str, str] = field(default_factory=dict)

    def register(self, name: str, handler_name: str) -> None:
        self.processors[name] = StreamingProcessor(name=name, handler_name=handler_name)
        self.pipeline_lookup[name] = handler_name

    def lookup(self, name: str) -> StreamingProcessor:
        if name not in self.processors:
            raise KeyError(f"unknown streaming processor: {name}")
        return self.processors[name]


def default_streaming_registry() -> StreamingRegistry:
    registry = StreamingRegistry()
    for name in (
        "resolve_source_events",
        "build_queue_state",
        "build_buffer_state",
        "build_window_state",
        "aggregate_events",
        "dispatch_detection",
        "dispatch_mitigation",
        "persist_checkpoint",
        "persist_session",
    ):
        registry.register(name, name)
    return registry
