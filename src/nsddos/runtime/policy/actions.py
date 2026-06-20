"""Dynamic policy action helpers."""

from __future__ import annotations

from nsddos.runtime.policy.contracts import POLICY_ACTIONS

ACTION_RANK = {
    "alert_only": 0,
    "rate_limit": 1,
    "drop_traffic": 2,
    "block_ip": 3,
    "quarantine_host": 4,
    "isolate_subnet": 5,
    "permanent_ban": 6,
}


def allowed_actions() -> tuple[str, ...]:
    return POLICY_ACTIONS


def action_rank(action: str) -> int:
    return ACTION_RANK[action]
