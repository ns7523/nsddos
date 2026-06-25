"""Live Floodlight adapter."""

from __future__ import annotations

from nsddos.providers.floodlight.provider import FloodlightProvider
from nsddos.runtime.providers.live.connection_pool import DeterministicConnectionPool


def collect_floodlight_telemetry(
    provider: FloodlightProvider,
    pool: DeterministicConnectionPool,
) -> dict[str, object]:
    switches_result = pool.get_json(
        f"{provider.api_url}/wm/core/controller/switches/json"
    )
    hosts_result = pool.get_json(f"{provider.api_url}/wm/device/")
    links_result = pool.get_json(f"{provider.api_url}/wm/topology/links/json")
    switches_payload = (
        switches_result.payload if isinstance(switches_result.payload, list) else []
    )
    hosts_payload = (
        hosts_result.payload if isinstance(hosts_result.payload, list) else []
    )
    links_payload = (
        links_result.payload if isinstance(links_result.payload, list) else []
    )
    switches = tuple(
        sorted(str(item.get("switchDPID", "unknown")) for item in switches_payload)
    )
    hosts = tuple(
        sorted(
            str(item.get("ipv4", ["unknown"])[0])
            for item in hosts_payload
            if isinstance(item, dict)
        )
    )
    return {
        "reachable": provider.is_reachable(),
        "latency_ms": max(
            switches_result.latency_ms, hosts_result.latency_ms, links_result.latency_ms
        ),
        "controller_port_open": provider.controller_port_open(),
        "switches": switches,
        "hosts": hosts,
        "links": tuple(links_payload),
        "malformed": not switches_result.ok,
    }
