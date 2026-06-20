"""Policy priority mapping."""

from __future__ import annotations

from nsddos.runtime.policy.actions import action_rank
from nsddos.runtime.policy.contracts_models import PolicyPriority


def priority_for_action(action: str) -> PolicyPriority:
    rank = action_rank(action)
    if rank >= 6:
        return PolicyPriority("CRITICAL", 4)
    if rank >= 4:
        return PolicyPriority("HIGH", 3)
    if rank >= 2:
        return PolicyPriority("MEDIUM", 2)
    return PolicyPriority("LOW", 1)
