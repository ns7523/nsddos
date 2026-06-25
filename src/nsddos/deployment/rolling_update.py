"""Deterministic rolling update plans."""

from __future__ import annotations

from nsddos.deployment.contracts import RollingUpdatePlan


def build_rolling_update_plan(container_count: int) -> RollingUpdatePlan:
    """Build deterministic rolling update plan."""
    batch_size = 1 if container_count <= 2 else 2
    return RollingUpdatePlan(
        strategy="rolling",
        batch_size=batch_size,
        max_unavailable=0,
        promotion_gates=("health_checks", "manifest_validation", "rollback_ready"),
        failure_stop_conditions=(
            "failed_health_probe",
            "network_policy_conflict",
            "missing_required_secret",
        ),
    )
