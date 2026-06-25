"""Typed live provider contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from nsddos.runtime.domain.versions import CONTRACT_VERSION, SCHEMA_VERSION


@dataclass(frozen=True)
class DistributionPoint:
    key: str
    value: float

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "value": self.value}


@dataclass(frozen=True)
class TopologyLink:
    source: str
    target: str

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "target": self.target}


@dataclass(frozen=True)
class TopologySnapshot:
    switches: tuple[str, ...] = field(default_factory=tuple)
    hosts: tuple[str, ...] = field(default_factory=tuple)
    controllers: tuple[str, ...] = field(default_factory=tuple)
    links: tuple[TopologyLink, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "switches": list(self.switches),
            "hosts": list(self.hosts),
            "controllers": list(self.controllers),
            "links": [item.to_dict() for item in self.links],
        }


@dataclass(frozen=True)
class ProviderHealthRecord:
    provider: str
    state: str
    reachable: bool
    latency_ms: float
    detail: str
    last_timestamp: str = ""
    error_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "state": self.state,
            "reachable": self.reachable,
            "latency_ms": self.latency_ms,
            "detail": self.detail,
            "last_timestamp": self.last_timestamp,
            "error_count": self.error_count,
        }


@dataclass(frozen=True)
class ProviderDiscoveryRecord:
    provider: str
    switches: tuple[str, ...] = field(default_factory=tuple)
    hosts: tuple[str, ...] = field(default_factory=tuple)
    controllers: tuple[str, ...] = field(default_factory=tuple)
    links: tuple[TopologyLink, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "switches": list(self.switches),
            "hosts": list(self.hosts),
            "controllers": list(self.controllers),
            "links": [item.to_dict() for item in self.links],
        }


@dataclass(frozen=True)
class ProviderDiagnosticRecord:
    provider: str
    latency_ms: float
    health_state: str
    error_count: int
    stale: bool
    anomalies: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "latency_ms": self.latency_ms,
            "health_state": self.health_state,
            "error_count": self.error_count,
            "stale": self.stale,
            "anomalies": list(self.anomalies),
        }


@dataclass(frozen=True)
class ControllerEventRecord:
    event_type: str
    provider: str
    subject: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "provider": self.provider,
            "subject": self.subject,
            "status": self.status,
        }


@dataclass(frozen=True)
class LiveTelemetrySnapshot:
    provider_source: str
    packet_rate: float
    byte_rate: float
    connection_rate: float
    syn_rate: float
    udp_rate: float
    icmp_rate: float
    active_flows: int
    dropped_packets: int
    source_ip_distribution: tuple[DistributionPoint, ...] = field(default_factory=tuple)
    destination_port_distribution: tuple[DistributionPoint, ...] = field(
        default_factory=tuple
    )
    topology_state: TopologySnapshot = field(default_factory=TopologySnapshot)
    controller_status: str = "unknown"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    health_state: str = "disconnected"
    provider_health: tuple[ProviderHealthRecord, ...] = field(default_factory=tuple)
    controller_events: tuple[ControllerEventRecord, ...] = field(default_factory=tuple)
    schema_version: str = SCHEMA_VERSION
    contract_version: str = CONTRACT_VERSION
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract_version": self.contract_version,
            "created_at": self.created_at,
            "provider_source": self.provider_source,
            "packet_rate": self.packet_rate,
            "byte_rate": self.byte_rate,
            "connection_rate": self.connection_rate,
            "syn_rate": self.syn_rate,
            "udp_rate": self.udp_rate,
            "icmp_rate": self.icmp_rate,
            "active_flows": self.active_flows,
            "dropped_packets": self.dropped_packets,
            "source_ip_distribution": [
                item.to_dict() for item in self.source_ip_distribution
            ],
            "destination_port_distribution": [
                item.to_dict() for item in self.destination_port_distribution
            ],
            "topology_state": self.topology_state.to_dict(),
            "controller_status": self.controller_status,
            "timestamp": self.timestamp.isoformat(),
            "health_state": self.health_state,
            "provider_health": [item.to_dict() for item in self.provider_health],
            "controller_events": [item.to_dict() for item in self.controller_events],
        }
