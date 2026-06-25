"""Deterministic worker inventory."""

from __future__ import annotations

from datetime import datetime

from nsddos.distributed.contracts import WORKER_TYPES, ClusterNode, WorkerAssignment


def assign_workers(
    nodes: tuple[ClusterNode, ...], scheduled_at: datetime
) -> tuple[WorkerAssignment, ...]:
    """Assign fixed worker types to nodes."""
    healthy_nodes = (
        tuple(
            node
            for node in nodes
            if node.state in {"healthy", "recovering", "degraded"}
        )
        or nodes
    )
    ordered_nodes = sorted(
        healthy_nodes, key=lambda node: (-node.capability_score, node.node_id)
    )
    assignments: list[WorkerAssignment] = []
    for index, worker_type in enumerate(WORKER_TYPES):
        node = ordered_nodes[index % len(ordered_nodes)]
        assignments.append(
            WorkerAssignment(
                worker_id=f"{worker_type}-worker",
                worker_type=worker_type,
                node_id=node.node_id,
                scheduled_at=scheduled_at.isoformat(),
                priority=index + 1,
            )
        )
    return tuple(assignments)
