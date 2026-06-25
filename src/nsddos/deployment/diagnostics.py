"""Deployment diagnostics builders."""

from __future__ import annotations

from nsddos.deployment.contracts import (
    AutoscalingPolicy,
    BackupSnapshot,
    DeploymentDiagnostics,
    DeploymentHealthState,
    RollbackState,
    SecretContract,
)


def build_deployment_diagnostics(
    health: DeploymentHealthState,
    autoscaling: AutoscalingPolicy,
    secret_contract: SecretContract,
    rollback_state: RollbackState,
    backup_snapshot: BackupSnapshot,
    manifest_count: int,
    health_latency_ms: float,
) -> DeploymentDiagnostics:
    """Build deployment diagnostics summary."""
    warnings: list[str] = []
    if secret_contract.missing_keys:
        warnings.append("missing_required_secrets")
    if health.state != "healthy":
        warnings.append("health_not_healthy")
    if autoscaling.max_replicas <= autoscaling.min_replicas:
        warnings.append("autoscaling_range_flat")
    return DeploymentDiagnostics(
        health_latency_ms=health_latency_ms,
        autoscaling_risk="low" if autoscaling.max_replicas >= 3 else "medium",
        missing_secret_count=len(secret_contract.missing_keys),
        rollback_ready=rollback_state.rollback_available,
        backup_available=backup_snapshot.available,
        manifest_count=manifest_count,
        warnings=tuple(warnings),
    )


def diagnostics_to_rows(diagnostics: DeploymentDiagnostics) -> list[tuple[str, str]]:
    """Convert diagnostics to CLI rows."""
    return [
        ("health_latency_ms", f"{diagnostics.health_latency_ms:.2f}"),
        ("autoscaling_risk", diagnostics.autoscaling_risk),
        ("missing_secret_count", str(diagnostics.missing_secret_count)),
        ("rollback_ready", str(diagnostics.rollback_ready)),
        ("backup_available", str(diagnostics.backup_available)),
        ("manifest_count", str(diagnostics.manifest_count)),
        ("warnings", ",".join(diagnostics.warnings) or "none"),
    ]
