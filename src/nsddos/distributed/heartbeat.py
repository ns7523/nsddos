"""Deterministic heartbeat/liveness summary."""

from __future__ import annotations

from nsddos.distributed.contracts import (
    ClusterNode,
    HeartbeatState,
    LeaderState,
    WorkerAssignment,
)


def build_heartbeat_state(
    nodes: tuple[ClusterNode, ...],
    leader_state: LeaderState,
    assignments: tuple[WorkerAssignment, ...],
) -> HeartbeatState:
    """Build heartbeat state without live probes."""
    live_nodes = tuple(
        node.node_id for node in nodes if node.state in {"healthy", "recovering"}
    )
    degraded_nodes = tuple(node.node_id for node in nodes if node.state == "degraded")
    failed_nodes = tuple(node.node_id for node in nodes if node.state == "failed")
    available = live_nodes + degraded_nodes
    worker_liveness = tuple(
        (assignment.worker_id, assignment.node_id in available)
        for assignment in assignments
    )
    return HeartbeatState(
        live_nodes=live_nodes,
        degraded_nodes=degraded_nodes,
        failed_nodes=failed_nodes,
        leader_alive=leader_state.primary_node in available,
        worker_liveness=worker_liveness,
    )
