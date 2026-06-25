"""Live telemetry validation."""

from __future__ import annotations

from datetime import datetime, timezone

from nsddos.runtime.providers.live.contracts import LiveTelemetrySnapshot


def validate_live_snapshot(snapshot: LiveTelemetrySnapshot) -> list[str]:
    errors: list[str] = []
    if (
        snapshot.packet_rate < 0
        or snapshot.byte_rate < 0
        or snapshot.connection_rate < 0
    ):
        errors.append("invalid_packet_counters")
    if snapshot.active_flows < 0 or snapshot.dropped_packets < 0:
        errors.append("invalid_active_flow_count")
    if not snapshot.provider_source:
        errors.append("missing_provider_source")
    if snapshot.health_state not in {
        "healthy",
        "degraded",
        "disconnected",
        "reconnecting",
    }:
        errors.append("invalid_health_state")
    if snapshot.timestamp.tzinfo is None:
        errors.append("missing_timestamp_timezone")
    age_seconds = max(
        0.0, (datetime.now(timezone.utc) - snapshot.timestamp).total_seconds()
    )
    if age_seconds > 300:
        errors.append("stale_provider_timestamp")
    if (
        not snapshot.topology_state.switches
        and not snapshot.topology_state.hosts
        and snapshot.health_state == "healthy"
    ):
        errors.append("invalid_topology_payload")
    if (
        any(item.state == "disconnected" for item in snapshot.provider_health)
        and snapshot.health_state == "healthy"
    ):
        errors.append("unreachable_provider_state")
    return errors
