"""Deterministic partition assignment."""

from __future__ import annotations

from nsddos.distributed.contracts import ClusterNode, PartitionAssignment


def assign_partitions(nodes: tuple[ClusterNode, ...], replication_factor: int, partition_count: int) -> tuple[PartitionAssignment, ...]:
    """Assign partitions round-robin over healthy nodes."""
    healthy_nodes = tuple(node for node in nodes if node.state != "failed") or nodes
    ordered = sorted(healthy_nodes, key=lambda node: node.node_id)
    assignments: list[PartitionAssignment] = []
    for index in range(partition_count):
        primary = ordered[index % len(ordered)]
        replica_nodes = []
        for replica_index in range(1, replication_factor):
            replica_nodes.append(ordered[(index + replica_index) % len(ordered)].node_id)
        assignments.append(
            PartitionAssignment(
                partition_id=f"partition-{index + 1}",
                partition_kind="telemetry" if index % 2 == 0 else "stream",
                node_id=primary.node_id,
                replica_node_ids=tuple(replica_nodes),
            )
        )
    return tuple(assignments)
