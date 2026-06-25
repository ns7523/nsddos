"""Live OVS adapter."""

from __future__ import annotations

from nsddos.providers.ovs.provider import OVSProvider


def collect_ovs_telemetry(provider: OVSProvider) -> dict[str, object]:
    state = provider.ovs_state()
    bridges = tuple(item.name for item in state.bridges)
    interfaces = tuple(
        sorted(name for item in state.bridges for name in item.interfaces)
    )
    dropped_packets = 0 if state.service_running else 0
    return {
        "reachable": state.installed and state.service_running,
        "latency_ms": 0.0,
        "bridges": bridges,
        "interfaces": interfaces,
        "active_connection_state": state.service_running
        and any(item.controller_connected for item in state.bridges),
        "dropped_packets": dropped_packets,
        "malformed": False,
    }
