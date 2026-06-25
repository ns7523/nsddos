"""Distributed checkpoint persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from io import TextIOWrapper

from nsddos.constants import RUNTIME_DIR
from nsddos.distributed.contracts import (
    ClusterNode,
    DistributedCheckpointState,
    PartitionAssignment,
    ReplicationState,
    WorkerAssignment,
)
from nsddos.runtime.persistence import atomic_write_json, read_json_checked

DISTRIBUTED_DIR = RUNTIME_DIR / "distributed"


def build_checkpoint_state(
    nodes: tuple[ClusterNode, ...],
    assignments: tuple[WorkerAssignment, ...],
    partitions: tuple[PartitionAssignment, ...],
    replication: ReplicationState,
) -> DistributedCheckpointState:
    """Build deterministic checkpoint state."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    node_offsets = tuple(
        (node.node_id, index)
        for index, node in enumerate(
            sorted(nodes, key=lambda item: item.node_id), start=1
        )
    )
    stream_offsets = tuple(
        (partition.partition_id, index * 100)
        for index, partition in enumerate(partitions, start=1)
    )
    state = (
        "corrupt"
        if not assignments
        else ("degraded" if any(node.state == "failed" for node in nodes) else "ready")
    )
    return DistributedCheckpointState(
        checkpoint_id=f"checkpoint-{timestamp}",
        state=state,
        node_offsets=node_offsets,
        stream_offsets=stream_offsets,
        replication_generation=f"replication-{replication.replication_factor}-{len(replication.target_nodes)}",
    )


def persist_checkpoint(
    payload: dict[str, object], *, lock_scope: TextIOWrapper | None = None
) -> None:
    """Persist latest checkpoint payload."""
    DISTRIBUTED_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_json(
        DISTRIBUTED_DIR / "checkpoint.json", payload, lock_scope=lock_scope
    )  # edge serialization


def latest_checkpoint_payload() -> dict:
    """Return latest checkpoint payload."""
    path = DISTRIBUTED_DIR / "checkpoint.json"
    if not path.exists():
        return {}
    return read_json_checked(path)
