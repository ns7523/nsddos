"""Typed simulation contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from nsddos.runtime.domain.versions import CONTRACT_VERSION, SCHEMA_VERSION

SIMULATION_ATTACK_TYPES = {
    "syn_flood",
    "udp_flood",
    "icmp_flood",
    "http_flood",
    "slowloris",
    "connection_exhaustion",
}

INTENSITY_LEVELS = {"low", "medium", "high"}
TARGET_KINDS = {"host", "subnet", "switch", "controller"}
PATTERN_NAMES = {"burst", "sustained", "exponential_ramp_up", "random_burst", "wave_attack"}


@dataclass(frozen=True)
class PacketMetadata:
    sequence_id: int
    protocol: str
    source_ip: str
    target_ip: str
    target_port: int
    size_bytes: int
    flags: str = ""
    payload_kind: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence_id": self.sequence_id,
            "protocol": self.protocol,
            "source_ip": self.source_ip,
            "target_ip": self.target_ip,
            "target_port": self.target_port,
            "size_bytes": self.size_bytes,
            "flags": self.flags,
            "payload_kind": self.payload_kind,
        }


@dataclass(frozen=True)
class PacketScheduleEntry:
    sequence_id: int
    emit_at_ms: int
    repeat_index: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence_id": self.sequence_id,
            "emit_at_ms": self.emit_at_ms,
            "repeat_index": self.repeat_index,
        }


@dataclass(frozen=True)
class ReplayTrafficRecord:
    sequence_id: int
    preserved_timestamp_ms: int
    protocol: str
    target_ip: str
    target_port: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence_id": self.sequence_id,
            "preserved_timestamp_ms": self.preserved_timestamp_ms,
            "protocol": self.protocol,
            "target_ip": self.target_ip,
            "target_port": self.target_port,
        }


@dataclass(frozen=True)
class TopologyPathRecord:
    path_type: str
    hops: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {"path_type": self.path_type, "hops": list(self.hops)}


@dataclass(frozen=True)
class TargetSelection:
    target_kind: str
    target_ip: str
    target_ports: tuple[int, ...] = field(default_factory=tuple)
    identifier: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_kind": self.target_kind,
            "target_ip": self.target_ip,
            "target_ports": list(self.target_ports),
            "identifier": self.identifier,
        }


@dataclass(frozen=True)
class AttackGeneratorProfile:
    attack_type: str
    protocol: str
    packet_rate: float
    byte_rate: float
    connection_rate: float
    duration_seconds: int
    source_ip_pool: tuple[str, ...]
    target_ports: tuple[int, ...]
    intensity_level: str
    pattern_name: str
    packet_size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "attack_type": self.attack_type,
            "protocol": self.protocol,
            "packet_rate": self.packet_rate,
            "byte_rate": self.byte_rate,
            "connection_rate": self.connection_rate,
            "duration_seconds": self.duration_seconds,
            "source_ip_pool": list(self.source_ip_pool),
            "target_ports": list(self.target_ports),
            "intensity_level": self.intensity_level,
            "pattern_name": self.pattern_name,
            "packet_size_bytes": self.packet_size_bytes,
        }


@dataclass(frozen=True)
class SimulationDiagnostics:
    packet_count: int
    byte_count: int
    schedule_duration_ms: int
    invalid_packet_bursts: tuple[str, ...] = field(default_factory=tuple)
    replay_drift_detected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_count": self.packet_count,
            "byte_count": self.byte_count,
            "schedule_duration_ms": self.schedule_duration_ms,
            "invalid_packet_bursts": list(self.invalid_packet_bursts),
            "replay_drift_detected": self.replay_drift_detected,
        }


@dataclass(frozen=True)
class AttackTrafficContract:
    attack_type: str
    target_ip: str
    packet_rate: float
    byte_rate: float
    connection_rate: float
    duration_seconds: int
    source_ip_pool: tuple[str, ...]
    target_ports: tuple[int, ...]
    intensity_level: str
    replay_mode: bool
    topology_path: tuple[str, ...]
    timestamp: datetime
    packet_schedule: tuple[PacketScheduleEntry, ...] = field(default_factory=tuple)
    packet_metadata: tuple[PacketMetadata, ...] = field(default_factory=tuple)
    replay_records: tuple[ReplayTrafficRecord, ...] = field(default_factory=tuple)
    target_kind: str = "host"
    pattern_name: str = "burst"
    diagnostics: SimulationDiagnostics = field(default_factory=lambda: SimulationDiagnostics(0, 0, 0))
    schema_version: str = SCHEMA_VERSION
    contract_version: str = CONTRACT_VERSION
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract_version": self.contract_version,
            "created_at": self.created_at,
            "attack_type": self.attack_type,
            "target_ip": self.target_ip,
            "packet_rate": self.packet_rate,
            "byte_rate": self.byte_rate,
            "connection_rate": self.connection_rate,
            "duration_seconds": self.duration_seconds,
            "source_ip_pool": list(self.source_ip_pool),
            "target_ports": list(self.target_ports),
            "intensity_level": self.intensity_level,
            "replay_mode": self.replay_mode,
            "topology_path": list(self.topology_path),
            "timestamp": self.timestamp.isoformat(),
            "packet_schedule": [item.to_dict() for item in self.packet_schedule],
            "packet_metadata": [item.to_dict() for item in self.packet_metadata],
            "replay_records": [item.to_dict() for item in self.replay_records],
            "target_kind": self.target_kind,
            "pattern_name": self.pattern_name,
            "diagnostics": self.diagnostics.to_dict(),
        }
