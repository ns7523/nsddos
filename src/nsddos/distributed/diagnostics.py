"""Distributed diagnostics."""

from __future__ import annotations

from collections import Counter

from nsddos.distributed.contracts import ClusterNode, DistributedDiagnostics, FailoverState, ReplicationState, WorkerAssignment


def build_diagnostics(
    nodes: tuple[ClusterNode, ...],
    assignments: tuple[WorkerAssignment, ...],
    replication: ReplicationState,
    failover: FailoverState,
) -> DistributedDiagnostics:
    """Build deterministic diagnostics payload."""
    distribution = Counter(assignment.node_id for assignment in assignments)
    return DistributedDiagnostics(
        node_health_metrics=tuple((node.node_id, node.state) for node in nodes),
        replication_lag_ms=replication.lag_ms,
        cluster_latency_ms=float(len(nodes) * 5 + len(assignments) * 2),
        worker_distribution_metrics=tuple(sorted((node_id, count) for node_id, count in distribution.items())),
        failover_metrics=(
            ("failover_available", str(failover.failover_available).lower()),
            ("failed_node_count", str(len(failover.failed_nodes))),
            ("reassigned_worker_count", str(len(failover.reassigned_workers))),
        ),
    )


def diagnostics_to_rows(diagnostics: DistributedDiagnostics) -> list[tuple[str, str]]:
    """Convert diagnostics to CLI rows."""
    return [
        ("replication_lag_ms", f"{diagnostics.replication_lag_ms:.2f}"),
        ("cluster_latency_ms", f"{diagnostics.cluster_latency_ms:.2f}"),
        ("node_health_metrics", ",".join(f"{node}:{state}" for node, state in diagnostics.node_health_metrics) or "none"),
        ("worker_distribution", ",".join(f"{node}:{count}" for node, count in diagnostics.worker_distribution_metrics) or "none"),
        ("failover_metrics", ",".join(f"{name}={value}" for name, value in diagnostics.failover_metrics) or "none"),
    ]
