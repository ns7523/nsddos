"""Deterministic rebalance planning."""

from __future__ import annotations

from nsddos.distributed.contracts import (
    FailoverState,
    PartitionAssignment,
    RebalancePlan,
    WorkerAssignment,
)


def build_rebalance_plan(
    failover_state: FailoverState,
    assignments: tuple[WorkerAssignment, ...],
    partitions: tuple[PartitionAssignment, ...],
) -> RebalancePlan:
    """Build worker and partition rebalance plan."""
    moved_workers = tuple(
        sorted(
            assignment.worker_id
            for assignment in assignments
            if assignment.node_id in failover_state.failed_nodes
        )
    )
    moved_partitions = tuple(
        sorted(
            partition.partition_id
            for partition in partitions
            if partition.node_id in failover_state.failed_nodes
        )
    )
    target_nodes = tuple(
        sorted(
            {
                partition.node_id
                for partition in partitions
                if partition.node_id not in failover_state.failed_nodes
            }
        )
    )
    return RebalancePlan(
        required=bool(failover_state.failed_nodes or moved_workers or moved_partitions),
        moved_workers=moved_workers,
        moved_partitions=moved_partitions,
        target_nodes=target_nodes,
        reason="failed_nodes_present" if failover_state.failed_nodes else "balanced",
    )
