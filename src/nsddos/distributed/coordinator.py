"""Deterministic worker/node coordinator."""

from __future__ import annotations

from nsddos.distributed.contracts import ClusterNode, WorkerAssignment


def coordinate_runtime(
    nodes: tuple[ClusterNode, ...], assignments: tuple[WorkerAssignment, ...]
) -> tuple[tuple[str, str], ...]:
    """Return stable worker-to-node mapping summary."""
    node_ids = {node.node_id for node in nodes}
    pairs = [
        (assignment.worker_id, assignment.node_id)
        for assignment in assignments
        if assignment.node_id in node_ids
    ]
    return tuple(sorted(pairs, key=lambda item: item[0]))
