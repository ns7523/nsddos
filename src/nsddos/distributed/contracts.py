"""Typed deterministic distributed runtime contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from nsddos.runtime.models import SCHEMA_VERSION

NODE_STATES = {"healthy", "degraded", "failed", "recovering"}
CHECKPOINT_STATES = {"ready", "degraded", "corrupt"}
CLUSTER_HEALTH_STATES = {"healthy", "degraded", "failed", "recovering"}
WORKER_TYPES = ("detection", "streaming", "mitigation", "policy", "ml")


@dataclass(frozen=True)
class ClusterNode:
    """Deterministic cluster node view."""

    node_id: str
    hostname: str
    roles: tuple[str, ...]
    capabilities: tuple[str, ...]
    state: str
    capability_score: int
    worker_capacity: int
    source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LeaderState:
    """Primary/standby leader state."""

    primary_node: str
    standby_node: str
    election_timeout_seconds: int
    re_election_required: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorkerAssignment:
    """Worker to node assignment."""

    worker_id: str
    worker_type: str
    node_id: str
    scheduled_at: str
    priority: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PartitionAssignment:
    """Workload partition assignment."""

    partition_id: str
    partition_kind: str
    node_id: str
    replica_node_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReplicationState:
    """Replicated state plan."""

    replication_factor: int
    replicated_resources: tuple[str, ...]
    target_nodes: tuple[str, ...]
    lag_ms: float
    state: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FailoverState:
    """Failover readiness and reassignment plan."""

    failover_available: bool
    leader_failover_node: str
    failed_nodes: tuple[str, ...]
    reassigned_workers: tuple[str, ...]
    recovery_state: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DistributedCheckpointState:
    """Checkpoint persistence state."""

    checkpoint_id: str
    state: str
    node_offsets: tuple[tuple[str, int], ...]
    stream_offsets: tuple[tuple[str, int], ...]
    replication_generation: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["node_offsets"] = [list(item) for item in self.node_offsets]
        payload["stream_offsets"] = [list(item) for item in self.stream_offsets]
        return payload


@dataclass(frozen=True)
class HeartbeatState:
    """Node and leader liveness summary."""

    live_nodes: tuple[str, ...]
    degraded_nodes: tuple[str, ...]
    failed_nodes: tuple[str, ...]
    leader_alive: bool
    worker_liveness: tuple[tuple[str, bool], ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["worker_liveness"] = [list(item) for item in self.worker_liveness]
        return payload


@dataclass(frozen=True)
class RebalancePlan:
    """Partition and worker rebalance state."""

    required: bool
    moved_workers: tuple[str, ...]
    moved_partitions: tuple[str, ...]
    target_nodes: tuple[str, ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DistributedDiagnostics:
    """Deterministic cluster diagnostics."""

    node_health_metrics: tuple[tuple[str, str], ...]
    replication_lag_ms: float
    cluster_latency_ms: float
    worker_distribution_metrics: tuple[tuple[str, int], ...]
    failover_metrics: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["node_health_metrics"] = [
            list(item) for item in self.node_health_metrics
        ]
        payload["worker_distribution_metrics"] = [
            list(item) for item in self.worker_distribution_metrics
        ]
        payload["failover_metrics"] = [list(item) for item in self.failover_metrics]
        return payload


@dataclass(frozen=True)
class DistributedRuntimeEvaluation:
    """Deterministic distributed runtime evaluation."""

    cluster_id: str
    active_nodes: int
    leader_node: str
    worker_count: int
    replication_factor: int
    partition_count: int
    cluster_health: str
    failover_available: bool
    checkpoint_state: str
    timestamp: datetime
    schema_version: str = SCHEMA_VERSION
    environment: str = "cluster"
    nodes: tuple[ClusterNode, ...] = field(default_factory=tuple)
    leader_state: LeaderState = field(
        default_factory=lambda: LeaderState(
            primary_node="",
            standby_node="",
            election_timeout_seconds=5,
            re_election_required=False,
        )
    )
    worker_assignments: tuple[WorkerAssignment, ...] = field(default_factory=tuple)
    partition_assignments: tuple[PartitionAssignment, ...] = field(
        default_factory=tuple
    )
    replication_state: ReplicationState = field(
        default_factory=lambda: ReplicationState(
            replication_factor=1,
            replicated_resources=(),
            target_nodes=(),
            lag_ms=0.0,
            state="ready",
        )
    )
    failover_state: FailoverState = field(
        default_factory=lambda: FailoverState(
            failover_available=False,
            leader_failover_node="",
            failed_nodes=(),
            reassigned_workers=(),
            recovery_state="recovering",
        )
    )
    checkpoint: DistributedCheckpointState = field(
        default_factory=lambda: DistributedCheckpointState(
            checkpoint_id="",
            state="degraded",
            node_offsets=(),
            stream_offsets=(),
            replication_generation="",
        )
    )
    heartbeat_state: HeartbeatState = field(
        default_factory=lambda: HeartbeatState(
            live_nodes=(),
            degraded_nodes=(),
            failed_nodes=(),
            leader_alive=False,
            worker_liveness=(),
        )
    )
    rebalance_plan: RebalancePlan = field(
        default_factory=lambda: RebalancePlan(
            required=False,
            moved_workers=(),
            moved_partitions=(),
            target_nodes=(),
            reason="",
        )
    )
    diagnostics: DistributedDiagnostics = field(
        default_factory=lambda: DistributedDiagnostics(
            node_health_metrics=(),
            replication_lag_ms=0.0,
            cluster_latency_ms=0.0,
            worker_distribution_metrics=(),
            failover_metrics=(),
        )
    )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.isoformat()
        payload["nodes"] = [item.to_dict() for item in self.nodes]
        payload["leader_state"] = self.leader_state.to_dict()
        payload["worker_assignments"] = [
            item.to_dict() for item in self.worker_assignments
        ]
        payload["partition_assignments"] = [
            item.to_dict() for item in self.partition_assignments
        ]
        payload["replication_state"] = self.replication_state.to_dict()
        payload["failover_state"] = self.failover_state.to_dict()
        payload["checkpoint"] = self.checkpoint.to_dict()
        payload["heartbeat_state"] = self.heartbeat_state.to_dict()
        payload["rebalance_plan"] = self.rebalance_plan.to_dict()
        payload["diagnostics"] = self.diagnostics.to_dict()
        return payload
