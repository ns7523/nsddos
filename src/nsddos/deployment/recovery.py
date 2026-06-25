"""Deployment recovery planning."""

from __future__ import annotations

from nsddos.deployment.contracts import DeploymentHealthState, RecoveryState


def build_recovery_state(health: DeploymentHealthState) -> RecoveryState:
    """Build deterministic recovery plan."""
    if health.state == "healthy":
        return RecoveryState(
            state="healthy",
            recommended_actions=("monitor_health", "retain_backup"),
            can_recover=True,
            reason="deployment contracts ready",
        )
    if health.environment_ready:
        return RecoveryState(
            state="recovering",
            recommended_actions=(
                "restart_docker_daemon",
                "re-run_health_checks",
                "confirm_provider_reachability",
            ),
            can_recover=True,
            reason="environment ready but runtime degraded",
        )
    return RecoveryState(
        state="failed",
        recommended_actions=(
            "install_docker",
            "create_missing_compose_file",
            "configure_required_secrets",
        ),
        can_recover=False,
        reason="environment prerequisites incomplete",
    )
