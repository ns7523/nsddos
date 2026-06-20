"""Deployment backup metadata."""

from __future__ import annotations

from datetime import datetime, timezone

from nsddos.constants import RUNTIME_DIR
from nsddos.deployment.contracts import BackupSnapshot


def build_backup_snapshot(environment: str) -> BackupSnapshot:
    """Build deterministic backup metadata."""
    timestamp = datetime.now(timezone.utc).isoformat()
    stamp = timestamp.replace(":", "").replace("-", "")
    return BackupSnapshot(
        backup_id=f"backup-{environment}-{stamp}",
        includes=("config", "runtime_state", "policy", "ml", "deployment"),
        storage_path=str(RUNTIME_DIR / "deployment" / "backups"),
        available=True,
        timestamp=timestamp,
    )
