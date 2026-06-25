"""Policy history persistence."""

from __future__ import annotations

from io import TextIOWrapper

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.persistence import (
    atomic_write_json,
    recover_json,
    read_json_checked,
)
from nsddos.runtime.policy.contracts_models import PolicyHistoryEntry

POLICY_DIR = RUNTIME_DIR / "policy"
HISTORY_PATH = POLICY_DIR / "history.json"


def load_history(
    *, lock_scope: TextIOWrapper | None = None
) -> tuple[PolicyHistoryEntry, ...]:
    payload = recover_json(HISTORY_PATH, {"entries": []}, lock_scope=lock_scope)
    return tuple(
        PolicyHistoryEntry(
            policy_id=str(item.get("policy_id", "")),
            attack_type=str(item.get("attack_type", "")),
            source_ip=str(item.get("source_ip", "")),
            source_subnet=str(item.get("source_subnet", "")),
            recommended_action=str(item.get("recommended_action", "alert_only")),
            confidence_score=float(item.get("confidence_score", 0.0)),
            escalation_level=int(item.get("escalation_level", 0)),
            timestamp=str(item.get("timestamp", "")),
        )
        for item in payload.get("entries", [])
    )


def save_history(
    entries: tuple[PolicyHistoryEntry, ...], *, lock_scope: TextIOWrapper | None = None
) -> None:
    POLICY_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_json(
        HISTORY_PATH,
        {"entries": [item.to_dict() for item in entries]},
        lock_scope=lock_scope,
    )


def latest_history_payload() -> dict[str, object]:
    if not HISTORY_PATH.exists():
        return {"entries": []}
    return read_json_checked(HISTORY_PATH)
