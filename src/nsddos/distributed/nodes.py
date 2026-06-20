"""Deterministic node registration and health."""

from __future__ import annotations

from typing import Any

from nsddos.distributed.contracts import ClusterNode

_HEALTH_WEIGHT = {
    "healthy": 4,
    "recovering": 3,
    "degraded": 2,
    "failed": 1,
}


def register_nodes(records: tuple[dict[str, Any], ...]) -> tuple[ClusterNode, ...]:
    """Normalize discovered node records."""
    nodes: list[ClusterNode] = []
    for record in sorted(records, key=lambda item: str(item.get("node_id", ""))):
        capabilities = tuple(sorted(str(cap) for cap in record.get("capabilities", ())))
        roles = tuple(sorted(str(role) for role in record.get("roles", ())))
        state = str(record.get("state", "healthy"))
        capability_score = len(capabilities) * 10 + len(roles) * 5 + _HEALTH_WEIGHT.get(state, 0)
        nodes.append(
            ClusterNode(
                node_id=str(record.get("node_id", "")),
                hostname=str(record.get("hostname", record.get("node_id", ""))),
                roles=roles,
                capabilities=capabilities,
                state=state,
                capability_score=capability_score,
                worker_capacity=max(1, int(record.get("worker_capacity", 5))),
                source=str(record.get("source", "unknown")),
            )
        )
    return tuple(nodes)


def active_nodes(nodes: tuple[ClusterNode, ...]) -> tuple[ClusterNode, ...]:
    """Return non-failed nodes."""
    return tuple(node for node in nodes if node.state != "failed")
