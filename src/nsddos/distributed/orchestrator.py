"""Deterministic distributed runtime orchestration."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from nsddos.constants import RUNTIME_DIR
from nsddos.distributed.checkpoint import build_checkpoint_state, persist_checkpoint
from nsddos.distributed.contracts import DistributedRuntimeEvaluation, FailoverState
from nsddos.distributed.coordinator import coordinate_runtime
from nsddos.distributed.diagnostics import build_diagnostics
from nsddos.distributed.discovery import discover_candidate_nodes
from nsddos.distributed.election import elect_leaders
from nsddos.distributed.failover import build_failover_state
from nsddos.distributed.heartbeat import build_heartbeat_state
from nsddos.distributed.nodes import active_nodes, register_nodes
from nsddos.distributed.partitions import assign_partitions
from nsddos.distributed.rebalancing import build_rebalance_plan
from nsddos.distributed.registry import latest_distributed_evaluation
from nsddos.distributed.replication import build_replication_state
from nsddos.distributed.scheduler import resolve_partition_count
from nsddos.distributed.validation import validate_distributed_evaluation
from nsddos.distributed.workers import assign_workers
from nsddos.runtime.persistence import atomic_write_json, locked_persistence_scope

DISTRIBUTED_DIR = RUNTIME_DIR / "distributed"


def _cluster_id(environment: str, node_ids: tuple[str, ...]) -> str:
    digest = hashlib.sha256(
        f"{environment}:{'|'.join(node_ids)}".encode("utf-8")
    ).hexdigest()[:16]
    return f"cluster:{digest}"


def _cluster_health(nodes_count: int, failed_count: int, degraded_count: int) -> str:
    if nodes_count == 0 or failed_count == nodes_count:
        return "failed"
    if failed_count or degraded_count:
        return "degraded"
    return "healthy"


def _persist(
    evaluation: DistributedRuntimeEvaluation, coordination: tuple[tuple[str, str], ...]
) -> None:
    DISTRIBUTED_DIR.mkdir(parents=True, exist_ok=True)
    payload = evaluation.to_dict()
    stamp = evaluation.timestamp.isoformat().replace(":", "").replace("-", "")
    with locked_persistence_scope(DISTRIBUTED_DIR) as lock_scope:
        atomic_write_json(
            DISTRIBUTED_DIR / f"distributed-{stamp}.json",
            payload,
            lock_scope=lock_scope,
        )
        atomic_write_json(
            DISTRIBUTED_DIR / "latest.json", payload, lock_scope=lock_scope
        )
        atomic_write_json(
            DISTRIBUTED_DIR / "registry.json",
            {
                "cluster_id": evaluation.cluster_id,
                "leaders": evaluation.leader_state.to_dict(),
                "nodes": [node.to_dict() for node in evaluation.nodes],
                "workers": [item.to_dict() for item in evaluation.worker_assignments],
                "partitions": [
                    item.to_dict() for item in evaluation.partition_assignments
                ],
                "coordination": [list(item) for item in coordination],
            },
            lock_scope=lock_scope,
        )
        atomic_write_json(
            DISTRIBUTED_DIR / "diagnostics.json",
            evaluation.diagnostics.to_dict(),
            lock_scope=lock_scope,
        )
        persist_checkpoint(evaluation.checkpoint.to_dict(), lock_scope=lock_scope)


def orchestrate_cluster_runtime(
    config: dict[str, Any], environment: str = "cluster"
) -> DistributedRuntimeEvaluation:
    """Compute deterministic distributed runtime state."""
    timestamp = datetime.now(timezone.utc)
    records = discover_candidate_nodes(config)
    nodes = register_nodes(records)
    active = active_nodes(nodes)
    leader_state = elect_leaders(
        active or nodes,
        election_timeout_seconds=int(
            config.get("distributed", {}).get("election_timeout_seconds", 5)
        ),
    )
    assignments = assign_workers(active or nodes, timestamp)
    replication_factor = min(
        int(config.get("distributed", {}).get("replication_factor", 2)),
        max(1, len(active or nodes)),
    )
    partition_count = resolve_partition_count(
        len(active or nodes), config.get("distributed", {}).get("partition_count")
    )
    partitions = assign_partitions(active or nodes, replication_factor, partition_count)
    replication = build_replication_state(replication_factor, partitions)
    checkpoint = build_checkpoint_state(nodes, assignments, partitions, replication)
    heartbeat = build_heartbeat_state(nodes, leader_state, assignments)
    failover = build_failover_state(leader_state, heartbeat, assignments)
    rebalance = build_rebalance_plan(failover, assignments, partitions)
    diagnostics = build_diagnostics(nodes, assignments, replication, failover)
    coordination = coordinate_runtime(nodes, assignments)
    cluster_health = _cluster_health(
        len(nodes), len(heartbeat.failed_nodes), len(heartbeat.degraded_nodes)
    )
    evaluation = DistributedRuntimeEvaluation(
        cluster_id=_cluster_id(environment, tuple(node.node_id for node in nodes)),
        active_nodes=len(active or nodes),
        leader_node=leader_state.primary_node,
        worker_count=len(assignments),
        replication_factor=replication_factor,
        partition_count=len(partitions),
        cluster_health=cluster_health,
        failover_available=failover.failover_available,
        checkpoint_state=checkpoint.state,
        timestamp=timestamp,
        environment=environment,
        nodes=nodes,
        leader_state=leader_state,
        worker_assignments=assignments,
        partition_assignments=partitions,
        replication_state=replication,
        failover_state=failover,
        checkpoint=checkpoint,
        heartbeat_state=heartbeat,
        rebalance_plan=rebalance,
        diagnostics=diagnostics,
    )
    errors = validate_distributed_evaluation(evaluation)
    if errors:
        raise ValueError(f"distributed evaluation invalid: {','.join(errors)}")
    _persist(evaluation, coordination)
    return evaluation


def distributed_health(
    config: dict[str, Any], environment: str = "cluster"
) -> DistributedRuntimeEvaluation:
    """Return latest cluster state or recompute."""
    latest = latest_distributed_evaluation()
    if latest and latest.get("environment") == environment:
        return orchestrate_cluster_runtime(config, environment=environment)
    return orchestrate_cluster_runtime(config, environment=environment)


def distributed_failover_plan(
    config: dict[str, Any], environment: str = "cluster"
) -> FailoverState:
    """Return deterministic failover plan."""
    return orchestrate_cluster_runtime(config, environment=environment).failover_state
