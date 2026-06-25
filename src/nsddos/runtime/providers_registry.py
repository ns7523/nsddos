"""Authoritative runtime provider registry."""

from __future__ import annotations

from typing import Any

from nsddos.providers.floodlight.provider import FloodlightProvider
from nsddos.providers.mininet.provider import MininetProvider
from nsddos.providers.ovs.provider import OVSProvider
from nsddos.providers.sflow.provider import SFlowProvider, resolve_sflowrt_api_url


def build_provider_registry(config: dict[str, Any]) -> dict[str, Any]:
    """Build providers from config once."""
    lab = config.get("lab", {})
    return {
        "floodlight": FloodlightProvider(api_url=f"http://127.0.0.1:{lab.get('floodlight_port', 8080)}"),
        "sflowrt": SFlowProvider(api_url=resolve_sflowrt_api_url(config)),
        "mininet": MininetProvider(
            controller_port=lab.get("controller_port", 6653),
            topology=lab.get("mininet_topology", "single,3"),
        ),
        "ovs": OVSProvider(
            collector_target=lab.get("ovs_sflow_target", "sflowrt:6343"),
            agent_interface=lab.get("ovs_agent_interface", "lo"),
            sampling=lab.get("ovs_sampling", 10),
            polling=lab.get("ovs_polling", 20),
        ),
    }


def collect_provider_status_from_registry(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Collect status from provider registry."""
    return {name: provider.status() for name, provider in registry.items()}
