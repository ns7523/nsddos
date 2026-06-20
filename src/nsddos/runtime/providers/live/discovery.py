"""Deterministic provider discovery."""

from __future__ import annotations

from nsddos.runtime.providers.live.contracts import ProviderDiscoveryRecord, TopologyLink


def discover_runtime_providers(
    *,
    floodlight_switches: tuple[str, ...],
    mininet_switches: tuple[str, ...],
    mininet_hosts: tuple[str, ...],
    controller_endpoint: str,
) -> tuple[ProviderDiscoveryRecord, ...]:
    mininet_links = tuple(TopologyLink("s1", host) for host in mininet_hosts)
    return (
        ProviderDiscoveryRecord(
            provider="floodlight",
            switches=floodlight_switches,
            controllers=(controller_endpoint,) if controller_endpoint else (),
        ),
        ProviderDiscoveryRecord(
            provider="mininet",
            switches=mininet_switches,
            hosts=mininet_hosts,
            controllers=(controller_endpoint,) if controller_endpoint else (),
            links=mininet_links,
        ),
    )
