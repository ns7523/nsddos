"""Live provider query adapters."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.providers.live import (
    build_provider_diagnostics,
    collect_live_telemetry,
    collect_provider_health,
    discover_runtime_providers,
)


def query_live_telemetry(config: dict[str, Any], query) -> dict[str, Any]:
    snapshot = collect_live_telemetry(config)
    payload = snapshot.to_dict()
    return {
        "items": [
            {
                "id": "live-telemetry",
                "type": "live_telemetry",
                "provider_source": payload["provider_source"],
                "packet_rate": payload["packet_rate"],
                "byte_rate": payload["byte_rate"],
                "active_flows": payload["active_flows"],
                "health_state": payload["health_state"],
                "controller_status": payload["controller_status"],
                "timestamp": payload["timestamp"],
            }
        ],
        "snapshot": payload,
    }


def query_provider_health(config: dict[str, Any], query) -> dict[str, Any]:
    snapshot = collect_live_telemetry(config)
    health = collect_provider_health(snapshot.provider_health)
    items = []
    for name, item in sorted(health.items()):
        items.append(
            {
                "id": f"provider-health:{name}",
                "type": "provider_health",
                "provider": name,
                "health_state": item["state"],
                "reachable": item["reachable"],
                "latency_ms": item["latency_ms"],
                "timestamp": snapshot.timestamp.isoformat(),
            }
        )
    return {"items": items}


def query_provider_discovery(config: dict[str, Any], query) -> dict[str, Any]:
    snapshot = collect_live_telemetry(config)
    discovery = discover_runtime_providers(
        floodlight_switches=tuple(snapshot.topology_state.switches),
        mininet_switches=tuple(snapshot.topology_state.switches),
        mininet_hosts=tuple(snapshot.topology_state.hosts),
        controller_endpoint=(
            snapshot.topology_state.controllers[0]
            if snapshot.topology_state.controllers
            else ""
        ),
    )
    items = []
    for item in discovery:
        payload = item.to_dict()
        items.append(
            {
                "id": f"provider-discovery:{item.provider}",
                "type": "provider_discovery",
                "provider": item.provider,
                "switch_count": len(payload["switches"]),
                "host_count": len(payload["hosts"]),
                "controller_count": len(payload["controllers"]),
                "timestamp": snapshot.timestamp.isoformat(),
            }
        )
    return {"items": items}


def query_provider_diagnostics(config: dict[str, Any], query) -> dict[str, Any]:
    snapshot = collect_live_telemetry(config)
    diagnostics = build_provider_diagnostics(snapshot)
    items = []
    for item in diagnostics:
        payload = item.to_dict()
        items.append(
            {
                "id": f"provider-diagnostics:{item.provider}",
                "type": "provider_diagnostics",
                "provider": item.provider,
                "health_state": payload["health_state"],
                "latency_ms": payload["latency_ms"],
                "error_count": payload["error_count"],
                "stale": payload["stale"],
                "timestamp": snapshot.timestamp.isoformat(),
            }
        )
    return {"items": items}
