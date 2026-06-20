"""Deterministic target selection."""

from __future__ import annotations

import ipaddress

from nsddos.providers.mininet.provider import MininetProvider
from nsddos.runtime.simulation.contracts import TargetSelection


HOST_IPS = {
    "h1": "10.0.0.1",
    "h2": "10.0.0.2",
    "h3": "10.0.0.3",
}


def _valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


def select_target(
    config: dict[str, object],
    *,
    target_kind: str,
    target_value: str = "",
) -> TargetSelection:
    mininet = MininetProvider(
        controller_port=int(config.get("lab", {}).get("controller_port", 6653)),  # type: ignore[arg-type]
        topology=str(config.get("lab", {}).get("mininet_topology", "single,3")),  # type: ignore[arg-type]
    )
    metadata = mininet.topology_metadata()
    if target_kind == "controller":
        return TargetSelection("controller", "127.0.0.1", (int(config.get("lab", {}).get("controller_port", 6653)),), metadata.controller)
    if target_kind == "switch":
        switch = target_value or metadata.switches[0]
        return TargetSelection("switch", HOST_IPS.get("h1", "10.0.0.1"), (6633,), switch)
    if target_kind == "subnet":
        subnet = target_value or "10.0.0.0"
        return TargetSelection("subnet", subnet, (80, 443), subnet)
    host = target_value or metadata.hosts[0]
    host_ip = HOST_IPS.get(host, host if _valid_ip(host) else "10.0.0.1")
    return TargetSelection("host", host_ip, (80, 443, 8080), host)
