"""Deterministic replication planning."""

from __future__ import annotations

from nsddos.distributed.contracts import PartitionAssignment, ReplicationState


def build_replication_state(
    replication_factor: int,
    partitions: tuple[PartitionAssignment, ...],
) -> ReplicationState:
    """Build replicated state plan."""
    target_nodes = sorted(
        {partition.node_id for partition in partitions}
        | {
            node_id
            for partition in partitions
            for node_id in partition.replica_node_ids
        }
    )
    lag_ms = float(len(partitions) * replication_factor * 3)
    return ReplicationState(
        replication_factor=replication_factor,
        replicated_resources=(
            "policy_state",
            "ml_model_state",
            "stream_checkpoints",
            "runtime_configuration",
        ),
        target_nodes=tuple(target_nodes),
        lag_ms=lag_ms,
        state="ready" if replication_factor >= 1 else "degraded",
    )
