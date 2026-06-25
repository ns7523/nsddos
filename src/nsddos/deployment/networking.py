"""Deployment networking contracts."""

from __future__ import annotations

from nsddos.constants import DEFAULT_FLOODLIGHT_PORT, DEFAULT_SFLOWRT_PORT
from nsddos.deployment.containers import manifest_path
from nsddos.deployment.contracts import NetworkingContract


def build_networking_contract(config: dict) -> NetworkingContract:
    """Build deterministic networking contract."""
    api_port = int(config.get("api_port", DEFAULT_SFLOWRT_PORT))
    dashboard_port = int(config.get("dashboard_port", 3000))
    floodlight_port = int(
        config.get("lab", {}).get("floodlight_port", DEFAULT_FLOODLIGHT_PORT)
    )
    return NetworkingContract(
        external_ports=(f"{dashboard_port}/tcp", f"{api_port}/tcp"),
        internal_ports=(f"{floodlight_port}/tcp", "6653/tcp", "6343/udp"),
        network_policies=(
            "deny-by-default-ingress",
            "allow-dashboard-to-api",
            "allow-runtime-to-controller",
        ),
        service_names=(
            "nsddos-ui",
            "nsddos-api",
            "nsddos-runtime",
            "floodlight",
            "sflowrt",
        ),
        source_manifest=str(manifest_path("kubernetes", "networkpolicy.yaml")),
    )
