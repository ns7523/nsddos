"""Deterministic deployment orchestration."""

from __future__ import annotations

from datetime import datetime, timezone

from nsddos.constants import PROJECT_ROOT, RUNTIME_DIR
from nsddos.deployment.autoscaling import build_autoscaling_policy
from nsddos.deployment.backup import build_backup_snapshot
from nsddos.deployment.containers import build_container_contracts
from nsddos.deployment.contracts import DeploymentEvaluation
from nsddos.deployment.diagnostics import build_deployment_diagnostics
from nsddos.deployment.healthcheck import compute_deployment_health
from nsddos.deployment.networking import build_networking_contract
from nsddos.deployment.recovery import build_recovery_state
from nsddos.deployment.registry import latest_deployment_payload
from nsddos.deployment.rollback import build_rollback_state
from nsddos.deployment.secrets import build_secret_contract
from nsddos.deployment.service_mesh import build_service_mesh_contract
from nsddos.deployment.rolling_update import build_rolling_update_plan
from nsddos.deployment.validation import validate_deployment_evaluation
from nsddos.runtime.persistence import atomic_write_json

DEPLOYMENT_DIR = RUNTIME_DIR / "deployment"


def _manifest_paths() -> tuple[str, ...]:
    root = PROJECT_ROOT / "deployment"
    manifests = (
        root / "docker" / "Dockerfile.prod",
        root / "docker" / "docker-compose.prod.yml",
        root / "kubernetes" / "deployment.yaml",
        root / "kubernetes" / "service.yaml",
        root / "kubernetes" / "hpa.yaml",
        root / "kubernetes" / "configmap.yaml",
        root / "kubernetes" / "secrets.yaml",
        root / "kubernetes" / "networkpolicy.yaml",
    )
    return tuple(str(path) for path in manifests)


def _deployment_state(health_state: str, has_missing_secrets: bool) -> str:
    if health_state == "failed":
        return "failed_validation"
    if has_missing_secrets or health_state == "degraded":
        return "degraded_dry_run"
    return "dry_run_ready"


def _persist(evaluation: DeploymentEvaluation) -> None:
    DEPLOYMENT_DIR.mkdir(parents=True, exist_ok=True)
    payload = evaluation.to_dict()
    stamp = evaluation.created_at.replace(":", "").replace("-", "")
    atomic_write_json(DEPLOYMENT_DIR / f"deployment-{stamp}.json", payload)
    atomic_write_json(DEPLOYMENT_DIR / "latest.json", payload)
    atomic_write_json(DEPLOYMENT_DIR / "backup.json", evaluation.backup_snapshot.to_dict())
    atomic_write_json(DEPLOYMENT_DIR / "rollback.json", evaluation.rollback_state.to_dict())
    atomic_write_json(DEPLOYMENT_DIR / "diagnostics.json", evaluation.diagnostics.to_dict())


def deploy_runtime_stack(config: dict, environment: str = "prod") -> DeploymentEvaluation:
    """Compute deterministic deployment evaluation without mutating live infrastructure."""
    manifests = _manifest_paths()
    container_contracts = build_container_contracts(environment)
    secret_contract = build_secret_contract()
    networking_contract = build_networking_contract(config)
    service_mesh = build_service_mesh_contract()
    health, health_latency_ms = compute_deployment_health(container_contracts)
    autoscaling_policy = build_autoscaling_policy(len(container_contracts))
    rolling_update = build_rolling_update_plan(len(container_contracts))
    backup_snapshot = build_backup_snapshot(environment)
    deployment_id = f"deploy-{environment}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    rollback_state = build_rollback_state(environment, deployment_id)
    recovery_state = build_recovery_state(health)
    diagnostics = build_deployment_diagnostics(
        health,
        autoscaling_policy,
        secret_contract,
        rollback_state,
        backup_snapshot,
        len(manifests),
        health_latency_ms,
    )
    evaluation = DeploymentEvaluation(
        deployment_id=deployment_id,
        environment=environment,
        deployment_state=_deployment_state(health.state, bool(secret_contract.missing_keys)),
        container_contracts=container_contracts,
        secret_contract=secret_contract,
        networking_contract=networking_contract,
        service_mesh=service_mesh,
        health=health,
        autoscaling_policy=autoscaling_policy,
        rolling_update=rolling_update,
        backup_snapshot=backup_snapshot,
        recovery_state=recovery_state,
        rollback_state=rollback_state,
        diagnostics=diagnostics,
        manifests=manifests,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    errors = validate_deployment_evaluation(evaluation)
    if errors:
        raise ValueError(f"deployment evaluation invalid: {','.join(errors)}")
    _persist(evaluation)
    return evaluation


def deployment_health(config: dict, environment: str = "prod") -> DeploymentEvaluation:
    """Return latest deployment evaluation or compute a fresh one."""
    latest = latest_deployment_payload()
    if latest and latest.get("environment") == environment:
        # Recompute to keep health signals current while preserving deterministic contract structure.
        return deploy_runtime_stack(config, environment=environment)
    return deploy_runtime_stack(config, environment=environment)


def rollback_runtime_stack(config: dict, environment: str = "prod") -> DeploymentEvaluation:
    """Compute a deterministic rollback deployment evaluation."""
    evaluation = deploy_runtime_stack(config, environment=environment)
    rollback_evaluation = DeploymentEvaluation(
        deployment_id=evaluation.deployment_id,
        environment=evaluation.environment,
        schema_version=evaluation.schema_version,
        deployment_state="rollback_planned",
        container_contracts=evaluation.container_contracts,
        secret_contract=evaluation.secret_contract,
        networking_contract=evaluation.networking_contract,
        service_mesh=evaluation.service_mesh,
        health=evaluation.health,
        autoscaling_policy=evaluation.autoscaling_policy,
        rolling_update=evaluation.rolling_update,
        backup_snapshot=evaluation.backup_snapshot,
        recovery_state=evaluation.recovery_state,
        rollback_state=evaluation.rollback_state,
        diagnostics=evaluation.diagnostics,
        manifests=evaluation.manifests,
        created_at=evaluation.created_at,
    )
    _persist(rollback_evaluation)
    return rollback_evaluation
