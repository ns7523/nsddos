"""Live provider telemetry collection."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from nsddos.runtime.models import FlowState, TelemetryFreshness, TelemetryState
from nsddos.runtime.providers.live.controller_events import normalize_controller_events
from nsddos.runtime.providers.live.contracts import LiveTelemetrySnapshot, TopologyLink, TopologySnapshot
from nsddos.runtime.providers.live.discovery import discover_runtime_providers
from nsddos.runtime.providers.live.floodlight import collect_floodlight_telemetry
from nsddos.runtime.providers.live.health import evaluate_provider_health
from nsddos.runtime.providers.live.mininet import collect_mininet_telemetry
from nsddos.runtime.providers.live.ovs import collect_ovs_telemetry
from nsddos.runtime.providers.live.registry import build_live_provider_registry
from nsddos.runtime.providers.live.sflow import collect_sflow_telemetry
from nsddos.runtime.providers.live.streaming import TelemetryStreamBuffer
from nsddos.runtime.providers.live.validation import validate_live_snapshot


def _live_enabled(config: dict[str, Any]) -> bool:
    return bool(config.get("runtime", {}).get("live", {}).get("enabled", False))


def collect_live_telemetry(config: dict[str, Any]) -> LiveTelemetrySnapshot:
    registry = build_live_provider_registry(config)
    sflow = collect_sflow_telemetry(registry.sflowrt, registry.pool)
    ovs = collect_ovs_telemetry(registry.ovs)
    mininet = collect_mininet_telemetry(registry.mininet)
    floodlight = collect_floodlight_telemetry(registry.floodlight, registry.pool)
    now = datetime.now(timezone.utc)
    health_records = (
        evaluate_provider_health("sflowrt", reachable=bool(sflow["reachable"]), latency_ms=float(sflow["latency_ms"]), malformed=bool(sflow["malformed"]), last_timestamp=now.isoformat(), error_count=0 if sflow["reachable"] else 1),
        evaluate_provider_health("ovs", reachable=bool(ovs["reachable"]), latency_ms=float(ovs["latency_ms"]), malformed=bool(ovs["malformed"]), last_timestamp=now.isoformat(), error_count=0 if ovs["reachable"] else 1),
        evaluate_provider_health("mininet", reachable=bool(mininet["reachable"]), latency_ms=float(mininet["latency_ms"]), malformed=bool(mininet["malformed"]), last_timestamp=now.isoformat(), error_count=0 if mininet["reachable"] else 1),
        evaluate_provider_health("floodlight", reachable=bool(floodlight["reachable"]), latency_ms=float(floodlight["latency_ms"]), malformed=bool(floodlight["malformed"]), last_timestamp=now.isoformat(), error_count=0 if floodlight["reachable"] else 1),
    )
    discovery = discover_runtime_providers(
        floodlight_switches=tuple(floodlight["switches"]),
        mininet_switches=tuple(mininet["switches"]),
        mininet_hosts=tuple(mininet["hosts"]),
        controller_endpoint=str(mininet["controller"]),
    )
    topology = TopologySnapshot(
        switches=tuple(sorted(set(tuple(mininet["switches"]) + tuple(floodlight["switches"])))),
        hosts=tuple(mininet["hosts"]),
        controllers=(str(mininet["controller"]),),
        links=tuple(TopologyLink("s1", host) for host in tuple(mininet["hosts"])),
    )
    snapshot = LiveTelemetrySnapshot(
        provider_source="live-provider-registry",
        packet_rate=float(sflow["packet_rate"]),
        byte_rate=float(sflow["byte_rate"]),
        connection_rate=float(sflow["connection_rate"]),
        syn_rate=float(sflow["syn_rate"]),
        udp_rate=float(sflow["udp_rate"]),
        icmp_rate=float(sflow["icmp_rate"]),
        active_flows=int(sflow["active_flows"]),
        dropped_packets=int(sflow["dropped_packets"]) + int(ovs["dropped_packets"]),
        source_ip_distribution=tuple(sflow["source_ip_distribution"]),
        destination_port_distribution=tuple(sflow["destination_port_distribution"]),
        topology_state=topology,
        controller_status="connected" if floodlight["controller_port_open"] and mininet["controller_reachable"] else "degraded",
        timestamp=now,
        health_state="healthy" if all(item.state == "healthy" for item in health_records) else "degraded" if any(item.state == "healthy" for item in health_records) else "disconnected",
        provider_health=health_records,
        controller_events=normalize_controller_events(discovery, health_records),
        created_at=now.isoformat(),
    )
    errors = validate_live_snapshot(snapshot)
    if errors:
        raise ValueError(f"live telemetry invalid: {','.join(errors)}")
    buffer = TelemetryStreamBuffer(batch_size=int(config.get("runtime", {}).get("live", {}).get("buffer_batch_size", 3)))
    buffer.push(snapshot)
    return snapshot


def live_snapshot_to_collection_state(snapshot: LiveTelemetrySnapshot) -> dict[str, dict[str, Any]]:
    provider_status = {item.provider: item.to_dict() for item in snapshot.provider_health}
    flow_state = FlowState(
        collector_reachable=snapshot.health_state in {"healthy", "degraded"},
        telemetry_present=snapshot.active_flows > 0,
        flow_count=snapshot.active_flows,
        switches_visible=list(snapshot.topology_state.switches),
        interfaces_visible=[item.key for item in snapshot.source_ip_distribution],
        metrics_changed=True,
        detail=f"live packet_rate={snapshot.packet_rate:.2f} byte_rate={snapshot.byte_rate:.2f}",
    )
    freshness = TelemetryFreshness(
        last_flow_timestamp=snapshot.timestamp.isoformat(),
        sample_interval_seconds=1.0,
        stale=snapshot.health_state in {"degraded", "disconnected"},
        detail=f"health_state={snapshot.health_state}",
    )
    telemetry = TelemetryState(
        collector_reachable=snapshot.health_state in {"healthy", "degraded"},
        flow_api_ready=snapshot.active_flows >= 0,
        metrics_available=True,
        topology_published=bool(snapshot.topology_state.switches),
        active_flow_count=snapshot.active_flows,
        last_flow_timestamp=snapshot.timestamp.isoformat(),
        update_interval_seconds=1.0,
        stale=snapshot.health_state in {"degraded", "disconnected"},
        visible_interfaces=[item.key for item in snapshot.source_ip_distribution],
    )
    return {
        "provider_status": provider_status,
        "flow_state": flow_state.to_dict(),
        "freshness_state": freshness.to_dict(),
        "telemetry_state": telemetry.to_dict(),
    }


def snapshot_to_detection_telemetry(snapshot: LiveTelemetrySnapshot) -> dict[str, Any]:
    top_source = snapshot.source_ip_distribution[0].key if snapshot.source_ip_distribution else "unknown"
    top_port = int(float(snapshot.destination_port_distribution[0].key)) if snapshot.destination_port_distribution else 0
    return {
        "provider_source": snapshot.provider_source,
        "timestamp": snapshot.timestamp.isoformat(),
        "sample_window_seconds": 1.0,
        "flows": [
            {
                "source": top_source,
                "destination_port": top_port,
                "packets": snapshot.packet_rate,
                "bytes": snapshot.byte_rate,
                "connections": snapshot.connection_rate,
                "syn_rate": snapshot.syn_rate,
                "udp_rate": snapshot.udp_rate,
                "icmp_rate": snapshot.icmp_rate,
                "duration": 1.0,
            }
        ],
        "flow_state": {
            "flow_count": snapshot.active_flows,
            "telemetry_present": snapshot.active_flows > 0,
            "detail": f"live snapshot health={snapshot.health_state}",
        },
        "telemetry_state": {
            "collector_reachable": snapshot.health_state in {"healthy", "degraded"},
            "active_flow_count": snapshot.active_flows,
        },
        "freshness_state": {
            "sample_interval_seconds": 1.0,
            "stale": snapshot.health_state in {"degraded", "disconnected"},
        },
    }
