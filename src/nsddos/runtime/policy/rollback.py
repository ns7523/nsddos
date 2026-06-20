"""Policy rollback persistence."""

from __future__ import annotations

from io import TextIOWrapper

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.persistence import atomic_write_json, recover_json, read_json_checked
from nsddos.runtime.policy.contracts_models import PolicyRollbackState

POLICY_DIR = RUNTIME_DIR / "policy"
ROLLBACK_PATH = POLICY_DIR / "rollback.json"


def save_rollback_state(state: PolicyRollbackState, *, lock_scope: TextIOWrapper | None = None) -> None:
    POLICY_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_json(ROLLBACK_PATH, state.to_dict(), lock_scope=lock_scope)


def load_rollback_state(*, lock_scope: TextIOWrapper | None = None) -> PolicyRollbackState | None:
    payload = recover_json(ROLLBACK_PATH, {}, lock_scope=lock_scope)
    if not payload:
        return None
    if not payload.get("rollback_id"):
        return None
    return PolicyRollbackState(
        rollback_id=str(payload.get("rollback_id", "")),
        restored_policy_id=str(payload.get("restored_policy_id", "")),
        restored_action=str(payload.get("restored_action", "alert_only")),
        restored_escalation_level=int(payload.get("restored_escalation_level", 0)),
        restored_threshold_score=float(payload.get("restored_threshold_score", 0.0)),
        timestamp=str(payload.get("timestamp", "")),
        restored=bool(payload.get("restored", False)),
    )


def latest_rollback_payload() -> dict[str, object]:
    if not ROLLBACK_PATH.exists():
        return {}
    return read_json_checked(ROLLBACK_PATH)
