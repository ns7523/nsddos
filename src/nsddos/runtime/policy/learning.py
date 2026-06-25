"""Policy learning persistence."""

from __future__ import annotations

from io import TextIOWrapper

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.persistence import (
    atomic_write_json,
    recover_json,
    read_json_checked,
)
from nsddos.runtime.policy.contracts_models import PolicyLearningState

POLICY_DIR = RUNTIME_DIR / "policy"
LEARNING_PATH = POLICY_DIR / "learning.json"


def load_learning_state(
    *, lock_scope: TextIOWrapper | None = None
) -> PolicyLearningState:
    payload = recover_json(LEARNING_PATH, {}, lock_scope=lock_scope)
    return PolicyLearningState(
        attack_signature_counts={
            str(k): int(v)
            for k, v in (payload.get("attack_signature_counts", {}) or {}).items()
        },
        source_ip_counts={
            str(k): int(v)
            for k, v in (payload.get("source_ip_counts", {}) or {}).items()
        },
        subnet_counts={
            str(k): int(v) for k, v in (payload.get("subnet_counts", {}) or {}).items()
        },
        mitigation_success_rate={
            str(k): float(v)
            for k, v in (payload.get("mitigation_success_rate", {}) or {}).items()
        },
    )


def save_learning_state(
    state: PolicyLearningState, *, lock_scope: TextIOWrapper | None = None
) -> None:
    POLICY_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_json(LEARNING_PATH, state.to_dict(), lock_scope=lock_scope)


def latest_learning_payload() -> dict[str, object]:
    if not LEARNING_PATH.exists():
        return {}
    return read_json_checked(LEARNING_PATH)
