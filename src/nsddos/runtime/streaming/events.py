"""Streaming event source conversion."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from nsddos.runtime.collection_replay import replay_latest_collection
from nsddos.runtime.domain.identifiers import deterministic_id
from nsddos.runtime.providers.live.telemetry import collect_live_telemetry
from nsddos.runtime.simulation import generate_attack_traffic
from nsddos.runtime.streaming.contracts import StreamEvent


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _live_events(config: dict[str, Any]) -> tuple[StreamEvent, ...]:
    snapshot = collect_live_telemetry(config)
    timestamp = snapshot.timestamp
    target_ip = snapshot.topology_state.hosts[0] if snapshot.topology_state.hosts else "10.0.0.1"
    source_points = snapshot.source_ip_distribution or ()
    if not source_points:
        source_points = (type("Point", (), {"key": "10.0.0.10", "value": snapshot.packet_rate or 1.0})(),)
    ordered = sorted(source_points, key=lambda item: (item.key, item.value))
    events = []
    for index, point in enumerate(ordered, start=1):
        packet_rate = float(point.value)
        protocol = "tcp"
        if snapshot.syn_rate >= snapshot.udp_rate and snapshot.syn_rate >= snapshot.icmp_rate:
            protocol = "tcp"
        elif snapshot.udp_rate >= snapshot.icmp_rate:
            protocol = "udp"
        else:
            protocol = "icmp"
        events.append(
            StreamEvent(
                event_id=deterministic_id("stream-event", f"live:{point.key}:{index}:{timestamp.isoformat()}"),
                source_type="live",
                packet_rate=packet_rate,
                byte_rate=max(snapshot.byte_rate / max(len(ordered), 1), packet_rate * 64.0),
                connection_rate=max(snapshot.connection_rate / max(len(ordered), 1), 1.0),
                protocol=protocol,
                source_ip=point.key,
                destination_ip=target_ip,
                timestamp=timestamp,
                sequence_number=index,
                freshness_state="valid" if snapshot.health_state == "healthy" else "degraded",
            )
        )
    return tuple(events)


def _simulation_events(config: dict[str, Any]) -> tuple[StreamEvent, ...]:
    contract = generate_attack_traffic(config, replay_mode=True)
    base_time = contract.timestamp
    events = []
    for index, packet in enumerate(contract.packet_metadata, start=1):
        schedule = contract.packet_schedule[index - 1]
        timestamp = base_time
        if schedule.emit_at_ms:
            timestamp = base_time.fromtimestamp(base_time.timestamp() + (schedule.emit_at_ms / 1000.0), tz=base_time.tzinfo)
        events.append(
            StreamEvent(
                event_id=deterministic_id("stream-event", f"simulation:{packet.sequence_id}:{timestamp.isoformat()}"),
                source_type="simulation",
                packet_rate=contract.packet_rate,
                byte_rate=contract.byte_rate,
                connection_rate=contract.connection_rate,
                protocol=packet.protocol,
                source_ip=packet.source_ip,
                destination_ip=packet.target_ip,
                timestamp=timestamp,
                sequence_number=packet.sequence_id,
                freshness_state="replay_only" if contract.replay_mode else "valid",
            )
        )
    return tuple(events)


def _collection_events() -> tuple[StreamEvent, ...]:
    replay = replay_latest_collection()
    payload = replay.get("collection", {}) if replay.get("available") else {}
    observed_at = payload.get("flow_state", {}).get("observed_at") or payload.get("telemetry_state", {}).get("last_flow_timestamp")
    timestamp = _parse_timestamp(str(observed_at)) if observed_at else datetime.now(timezone.utc)
    flow_state = payload.get("flow_state", {})
    telemetry_state = payload.get("telemetry_state", {})
    flow_count = int(flow_state.get("flow_count", 0))
    packet_rate = float(flow_count or 1)
    byte_rate = packet_rate * 64.0
    return (
        StreamEvent(
            event_id=deterministic_id("stream-event", f"collection:{timestamp.isoformat()}:{flow_count}"),
            source_type="collection",
            packet_rate=packet_rate,
            byte_rate=byte_rate,
            connection_rate=float(flow_count),
            protocol="tcp",
            source_ip="10.0.0.10",
            destination_ip="10.0.0.1",
            timestamp=timestamp,
            sequence_number=1,
            freshness_state="stale" if telemetry_state.get("stale", False) else "valid",
        ),
    )


def resolve_source_events(config: dict[str, Any]) -> tuple[str, tuple[StreamEvent, ...]]:
    if config.get("runtime", {}).get("live", {}).get("enabled", False):
        return "live", _live_events(config)
    if config.get("runtime", {}).get("simulation", {}).get("source_enabled", False):
        return "simulation", _simulation_events(config)
    return "collection", _collection_events()
