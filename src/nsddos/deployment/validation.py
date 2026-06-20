"""Deployment validation rules."""

from __future__ import annotations

from nsddos.deployment.contracts import DEPLOYMENT_STATES, HEALTH_STATES, DeploymentEvaluation, RollbackState


def validate_deployment_evaluation(evaluation: DeploymentEvaluation) -> list[str]:
    """Validate deployment evaluation."""
    errors: list[str] = []
    if evaluation.deployment_state not in DEPLOYMENT_STATES:
        errors.append("invalid_deployment_state")
    if evaluation.health.state not in HEALTH_STATES:
        errors.append("invalid_health_state")
    if not evaluation.container_contracts:
        errors.append("missing_container_contracts")
    if not evaluation.manifests:
        errors.append("missing_manifests")
    if (
        evaluation.secret_contract.missing_keys
        and evaluation.health.state == "healthy"
        and evaluation.deployment_state == "dry_run_ready"
    ):
        errors.append("healthy_with_missing_secrets")
    if evaluation.autoscaling_policy.max_replicas < evaluation.autoscaling_policy.min_replicas:
        errors.append("invalid_autoscaling_range")
    if not evaluation.rollback_state.rollback_steps:
        errors.append("missing_rollback_steps")
    if evaluation.networking_contract.external_ports and not evaluation.networking_contract.service_names:
        errors.append("networking_service_mismatch")
    return errors


def validate_rollback_state(rollback: RollbackState) -> list[str]:
    """Validate rollback state."""
    errors: list[str] = []
    if not rollback.rollback_id:
        errors.append("missing_rollback_id")
    if rollback.rollback_available and not rollback.rollback_steps:
        errors.append("rollback_steps_missing")
    if not rollback.target_version:
        errors.append("missing_target_version")
    return errors
