"""Deployment rollback planning."""

from __future__ import annotations

from datetime import datetime, timezone

from nsddos.constants import RUNTIME_DIR
from nsddos.deployment.contracts import RollbackState
from nsddos.runtime.persistence import read_json_checked

ROLLBACK_PATH = RUNTIME_DIR / "deployment" / "rollback.json"
LATEST_PATH = RUNTIME_DIR / "deployment" / "latest.json"


def latest_rollback_state() -> dict:
    """Return latest rollback payload if present."""
    if not ROLLBACK_PATH.exists():
        return {}
    return read_json_checked(ROLLBACK_PATH)


def build_rollback_state(environment: str, deployment_id: str) -> RollbackState:
    """Build deterministic rollback metadata."""
    timestamp = datetime.now(timezone.utc).isoformat()
    target_version = "latest-known-good"
    if LATEST_PATH.exists():
        try:
            latest = read_json_checked(LATEST_PATH)
            target_version = str(latest.get("deployment_id", target_version))
        except Exception:
            target_version = "latest-known-good"
    return RollbackState(
        rollback_id=f"rollback-{deployment_id}",
        rollback_available=True,
        target_version=target_version,
        rollback_steps=(
            "restore_previous_manifests",
            "restore_backup_metadata",
            "re-run_deployment_health",
        ),
        reason=f"dry-run rollback plan for {environment}",
        timestamp=timestamp,
    )
