"""Deterministic failover planning."""

from __future__ import annotations

from nsddos.distributed.contracts import FailoverState, HeartbeatState, LeaderState, WorkerAssignment


def build_failover_state(
    leader_state: LeaderState,
    heartbeat: HeartbeatState,
    assignments: tuple[WorkerAssignment, ...],
) -> FailoverState:
    """Build failover readiness state."""
    failed_nodes = heartbeat.failed_nodes
    reassigned = tuple(sorted(assignment.worker_id for assignment in assignments if assignment.node_id in failed_nodes))
    leader_failover_node = leader_state.standby_node if not heartbeat.leader_alive else leader_state.primary_node
    return FailoverState(
        failover_available=bool(leader_state.standby_node or not failed_nodes),
        leader_failover_node=leader_failover_node,
        failed_nodes=failed_nodes,
        reassigned_workers=reassigned,
        recovery_state="recovering" if failed_nodes else "healthy",
    )
