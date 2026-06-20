"""Typed deterministic deployment contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from nsddos.runtime.models import SCHEMA_VERSION

DEPLOYMENT_STATES = {
    "dry_run_ready",
    "degraded_dry_run",
    "failed_validation",
    "rollback_planned",
}
HEALTH_STATES = {"healthy", "degraded", "failed", "recovering"}


@dataclass(frozen=True)
class ContainerContract:
    """Dry-run container specification."""

    name: str
    image: str
    command: str
    ports: tuple[str, ...] = ()
    environment_keys: tuple[str, ...] = ()
    mounts: tuple[str, ...] = ()
    replicas: int = 1
    source_manifest: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SecretContract:
    """Required secret inventory without values."""

    required_keys: tuple[str, ...]
    optional_keys: tuple[str, ...] = ()
    missing_keys: tuple[str, ...] = ()
    rotation_window_days: int = 90
    source: str = "environment"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NetworkingContract:
    """Deterministic networking description."""

    external_ports: tuple[str, ...]
    internal_ports: tuple[str, ...]
    network_policies: tuple[str, ...]
    service_names: tuple[str, ...]
    source_manifest: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ServiceMeshContract:
    """Service dependency contract."""

    services: tuple[str, ...]
    dependencies: tuple[tuple[str, str], ...]
    controllers: tuple[str, ...] = ()
    providers: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["dependencies"] = [list(item) for item in self.dependencies]
        return payload


@dataclass(frozen=True)
class DeploymentHealthState:
    """Deployment health summary."""

    state: str
    service_health: str
    environment_ready: bool
    docker_installed: bool
    docker_daemon_running: bool
    compose_available: bool
    detail: str
    checks: tuple[tuple[str, str], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["checks"] = [list(item) for item in self.checks]
        return payload


@dataclass(frozen=True)
class AutoscalingPolicy:
    """Deterministic autoscaling thresholds."""

    min_replicas: int
    max_replicas: int
    cpu_percent_threshold: int
    memory_percent_threshold: int
    request_rate_threshold: int
    scale_up_step: int = 1
    scale_down_step: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RollingUpdatePlan:
    """Deterministic rollout plan."""

    strategy: str
    batch_size: int
    max_unavailable: int
    promotion_gates: tuple[str, ...]
    failure_stop_conditions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BackupSnapshot:
    """Backup metadata only."""

    backup_id: str
    includes: tuple[str, ...]
    storage_path: str
    available: bool
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecoveryState:
    """Recovery plan metadata."""

    state: str
    recommended_actions: tuple[str, ...]
    can_recover: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RollbackState:
    """Rollback plan metadata."""

    rollback_id: str
    rollback_available: bool
    target_version: str
    rollback_steps: tuple[str, ...]
    reason: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DeploymentDiagnostics:
    """Deployment diagnostics summary."""

    health_latency_ms: float
    autoscaling_risk: str
    missing_secret_count: int
    rollback_ready: bool
    backup_available: bool
    manifest_count: int
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DeploymentEvaluation:
    """Deterministic deployment evaluation."""

    deployment_id: str
    environment: str
    schema_version: str = SCHEMA_VERSION
    deployment_state: str = "dry_run_ready"
    container_contracts: tuple[ContainerContract, ...] = ()
    secret_contract: SecretContract = field(default_factory=lambda: SecretContract(required_keys=()))
    networking_contract: NetworkingContract = field(
        default_factory=lambda: NetworkingContract(external_ports=(), internal_ports=(), network_policies=(), service_names=())
    )
    service_mesh: ServiceMeshContract = field(default_factory=lambda: ServiceMeshContract(services=(), dependencies=()))
    health: DeploymentHealthState = field(
        default_factory=lambda: DeploymentHealthState(
            state="degraded",
            service_health="unknown",
            environment_ready=False,
            docker_installed=False,
            docker_daemon_running=False,
            compose_available=False,
            detail="uninitialized",
        )
    )
    autoscaling_policy: AutoscalingPolicy = field(
        default_factory=lambda: AutoscalingPolicy(
            min_replicas=1,
            max_replicas=1,
            cpu_percent_threshold=70,
            memory_percent_threshold=75,
            request_rate_threshold=100,
        )
    )
    rolling_update: RollingUpdatePlan = field(
        default_factory=lambda: RollingUpdatePlan(
            strategy="rolling",
            batch_size=1,
            max_unavailable=0,
            promotion_gates=("health_checks",),
            failure_stop_conditions=("failed_health",),
        )
    )
    backup_snapshot: BackupSnapshot = field(
        default_factory=lambda: BackupSnapshot(
            backup_id="",
            includes=(),
            storage_path="",
            available=False,
            timestamp="",
        )
    )
    recovery_state: RecoveryState = field(
        default_factory=lambda: RecoveryState(state="recovering", recommended_actions=(), can_recover=False, reason="uninitialized")
    )
    rollback_state: RollbackState = field(
        default_factory=lambda: RollbackState(
            rollback_id="",
            rollback_available=False,
            target_version="",
            rollback_steps=(),
            reason="uninitialized",
            timestamp="",
        )
    )
    diagnostics: DeploymentDiagnostics = field(
        default_factory=lambda: DeploymentDiagnostics(
            health_latency_ms=0.0,
            autoscaling_risk="unknown",
            missing_secret_count=0,
            rollback_ready=False,
            backup_available=False,
            manifest_count=0,
        )
    )
    manifests: tuple[str, ...] = ()
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["container_contracts"] = [item.to_dict() for item in self.container_contracts]
        payload["secret_contract"] = self.secret_contract.to_dict()
        payload["networking_contract"] = self.networking_contract.to_dict()
        payload["service_mesh"] = self.service_mesh.to_dict()
        payload["health"] = self.health.to_dict()
        payload["autoscaling_policy"] = self.autoscaling_policy.to_dict()
        payload["rolling_update"] = self.rolling_update.to_dict()
        payload["backup_snapshot"] = self.backup_snapshot.to_dict()
        payload["recovery_state"] = self.recovery_state.to_dict()
        payload["rollback_state"] = self.rollback_state.to_dict()
        payload["diagnostics"] = self.diagnostics.to_dict()
        return payload
