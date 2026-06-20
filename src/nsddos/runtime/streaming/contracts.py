"""Typed runtime streaming contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from nsddos.runtime.domain.versions import CONTRACT_VERSION, SCHEMA_VERSION

BACKPRESSURE_STATES = {"normal", "congested", "throttled", "overflow"}
STREAM_WINDOW_KINDS = {"sliding", "tumbling", "fixed_time"}
STREAM_SOURCE_TYPES = {"live", "simulation", "collection"}


@dataclass(frozen=True)
class StreamEvent:
    event_id: str
    source_type: str
    packet_rate: float
    byte_rate: float
    connection_rate: float
    protocol: str
    source_ip: str
    destination_ip: str
    timestamp: datetime
    sequence_number: int
    freshness_state: str
    destination_port: int = 0
    duration_seconds: float = 0.0
    flags: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "source_type": self.source_type,
            "packet_rate": self.packet_rate,
            "byte_rate": self.byte_rate,
            "connection_rate": self.connection_rate,
            "protocol": self.protocol,
            "source_ip": self.source_ip,
            "destination_ip": self.destination_ip,
            "timestamp": self.timestamp.isoformat(),
            "sequence_number": self.sequence_number,
            "freshness_state": self.freshness_state,
            "destination_port": self.destination_port,
            "duration_seconds": self.duration_seconds,
            "flags": self.flags,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class StreamQueueState:
    events: tuple[StreamEvent, ...] = field(default_factory=tuple)
    queue_depth: int = 0
    enqueued_count: int = 0
    dequeued_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "events": [item.to_dict() for item in self.events],
            "queue_depth": self.queue_depth,
            "enqueued_count": self.enqueued_count,
            "dequeued_count": self.dequeued_count,
        }


@dataclass(frozen=True)
class StreamBufferState:
    events: tuple[StreamEvent, ...] = field(default_factory=tuple)
    max_size: int = 0
    dropped_events: int = 0
    overflowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "events": [item.to_dict() for item in self.events],
            "max_size": self.max_size,
            "dropped_events": self.dropped_events,
            "overflowed": self.overflowed,
        }


@dataclass(frozen=True)
class StreamWindow:
    window_id: str
    start_timestamp: str
    end_timestamp: str
    events: tuple[StreamEvent, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "events": [item.to_dict() for item in self.events],
        }


@dataclass(frozen=True)
class StreamWindowState:
    window_kind: str
    window_seconds: int
    windows: tuple[StreamWindow, ...] = field(default_factory=tuple)
    active_events: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_kind": self.window_kind,
            "window_seconds": self.window_seconds,
            "windows": [item.to_dict() for item in self.windows],
            "active_events": self.active_events,
        }


@dataclass(frozen=True)
class ProtocolAggregate:
    protocol: str
    event_count: int
    packet_rate: float
    byte_rate: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": self.protocol,
            "event_count": self.event_count,
            "packet_rate": self.packet_rate,
            "byte_rate": self.byte_rate,
        }


@dataclass(frozen=True)
class StreamAggregation:
    total_packet_rate: float
    total_byte_rate: float
    total_connection_rate: float
    event_count: int
    protocol_breakdown: tuple[ProtocolAggregate, ...] = field(default_factory=tuple)
    attack_pattern: str = "normal"
    target_ip: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_packet_rate": self.total_packet_rate,
            "total_byte_rate": self.total_byte_rate,
            "total_connection_rate": self.total_connection_rate,
            "event_count": self.event_count,
            "protocol_breakdown": [item.to_dict() for item in self.protocol_breakdown],
            "attack_pattern": self.attack_pattern,
            "target_ip": self.target_ip,
        }


@dataclass(frozen=True)
class StreamBackpressureState:
    state: str
    queue_depth: int
    buffer_pressure: float
    dropped_events: int = 0
    throttled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "queue_depth": self.queue_depth,
            "buffer_pressure": self.buffer_pressure,
            "dropped_events": self.dropped_events,
            "throttled": self.throttled,
        }


@dataclass(frozen=True)
class StreamCheckpoint:
    checkpoint_id: str
    session_id: str
    event_offset: int
    queue_state: StreamQueueState
    buffer_state: StreamBufferState
    sequence_number: int
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "session_id": self.session_id,
            "event_offset": self.event_offset,
            "queue_state": self.queue_state.to_dict(),
            "buffer_state": self.buffer_state.to_dict(),
            "sequence_number": self.sequence_number,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class StreamSession:
    session_id: str
    source_mode: str
    session_start: datetime
    session_state: str
    processed_events_count: int
    last_checkpoint_id: str = ""
    last_sequence_number: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "source_mode": self.source_mode,
            "session_start": self.session_start.isoformat(),
            "session_state": self.session_state,
            "processed_events_count": self.processed_events_count,
            "last_checkpoint_id": self.last_checkpoint_id,
            "last_sequence_number": self.last_sequence_number,
        }


@dataclass(frozen=True)
class StreamingDiagnostics:
    queue_latency_ms: float
    processing_throughput: float
    dropped_event_count: int
    buffer_pressure: float
    session_health: str
    checkpoint_lag: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "queue_latency_ms": self.queue_latency_ms,
            "processing_throughput": self.processing_throughput,
            "dropped_event_count": self.dropped_event_count,
            "buffer_pressure": self.buffer_pressure,
            "session_health": self.session_health,
            "checkpoint_lag": self.checkpoint_lag,
        }


@dataclass(frozen=True)
class StreamingEvaluation:
    session: StreamSession
    queue_state: StreamQueueState
    buffer_state: StreamBufferState
    window_state: StreamWindowState
    aggregation: StreamAggregation
    backpressure: StreamBackpressureState
    checkpoint: StreamCheckpoint
    diagnostics: StreamingDiagnostics
    stream_state: str
    active_events: int
    dropped_events: int
    throughput: float
    timestamp: datetime
    detection_payload: dict[str, Any] = field(default_factory=dict)
    ml_payload: dict[str, Any] = field(default_factory=dict)
    policy_payload: dict[str, Any] = field(default_factory=dict)
    mitigation_payload: dict[str, Any] = field(default_factory=dict)
    source_events: tuple[StreamEvent, ...] = field(default_factory=tuple)
    schema_version: str = SCHEMA_VERSION
    contract_version: str = CONTRACT_VERSION
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract_version": self.contract_version,
            "created_at": self.created_at,
            "session": self.session.to_dict(),
            "queue_state": self.queue_state.to_dict(),
            "buffer_state": self.buffer_state.to_dict(),
            "window_state": self.window_state.to_dict(),
            "aggregation": self.aggregation.to_dict(),
            "backpressure": self.backpressure.to_dict(),
            "checkpoint": self.checkpoint.to_dict(),
            "diagnostics": self.diagnostics.to_dict(),
            "stream_state": self.stream_state,
            "active_events": self.active_events,
            "dropped_events": self.dropped_events,
            "throughput": self.throughput,
            "timestamp": self.timestamp.isoformat(),
            "detection_payload": self.detection_payload,
            "ml_payload": self.ml_payload,
            "policy_payload": self.policy_payload,
            "mitigation_payload": self.mitigation_payload,
            "source_events": [item.to_dict() for item in self.source_events],
        }
