"""Live Mininet adapter."""

from __future__ import annotations

from nsddos.providers.mininet.provider import MininetProvider


def collect_mininet_telemetry(provider: MininetProvider) -> dict[str, object]:
    status = provider.status()
    metadata = provider.topology_metadata()
    return {
        "reachable": bool(status.get("installed")),
        "latency_ms": 0.0,
        "running": bool(status.get("running")),
        "switches": tuple(metadata.switches),
        "hosts": tuple(metadata.hosts),
        "links": tuple(metadata.links),
        "controller": metadata.controller,
        "controller_reachable": metadata.controller_reachable,
        "malformed": False,
    }
