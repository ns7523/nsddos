"""Distributed evaluation validation."""

from __future__ import annotations

from nsddos.distributed.contracts import CHECKPOINT_STATES, CLUSTER_HEALTH_STATES, DistributedRuntimeEvaluation, NODE_STATES, WORKER_TYPES


def validate_distributed_evaluation(evaluation: DistributedRuntimeEvaluation) -> list[str]:
    """Validate cluster evaluation."""
    errors: list[str] = []
    if evaluation.active_nodes < 1:
        errors.append("invalid_active_nodes")
    if evaluation.cluster_health not in CLUSTER_HEALTH_STATES:
        errors.append("invalid_cluster_health")
    if evaluation.checkpoint_state not in CHECKPOINT_STATES:
        errors.append("invalid_checkpoint_state")
    if evaluation.leader_state.primary_node and evaluation.leader_state.primary_node == evaluation.leader_state.standby_node:
        errors.append("leader_conflict")
    node_ids = [node.node_id for node in evaluation.nodes]
    if len(node_ids) != len(set(node_ids)):
        errors.append("duplicate_node_registration")
    for node in evaluation.nodes:
        if node.state not in NODE_STATES:
            errors.append(f"invalid_node_state:{node.node_id}")
    worker_types = [assignment.worker_type for assignment in evaluation.worker_assignments]
    if tuple(sorted(worker_types)) != tuple(sorted(WORKER_TYPES)):
        errors.append("worker_assignment_incomplete")
    if evaluation.replication_factor < 1:
        errors.append("invalid_replication_factor")
    if evaluation.replication_factor > evaluation.active_nodes:
        errors.append("replication_exceeds_active_nodes")
    if not evaluation.checkpoint.replication_generation:
        errors.append("checkpoint_corruption")
    if evaluation.replication_state.state not in {"ready", "degraded", "corrupt"}:
        errors.append("replication_corruption")
    if evaluation.failover_available and not evaluation.failover_state.leader_failover_node:
        errors.append("failover_inconsistency")
    return errors
