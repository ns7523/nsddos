"""Policy conflict resolution."""

from __future__ import annotations

from nsddos.runtime.policy.actions import action_rank
from nsddos.runtime.policy.contracts_models import PolicyConflictResolution


def resolve_conflicts(candidates: tuple[str, ...]) -> PolicyConflictResolution:
    ordered = tuple(
        sorted(set(candidates), key=lambda item: (-action_rank(item), item))
    )
    selected = ordered[0] if ordered else "alert_only"
    return PolicyConflictResolution(
        candidates=ordered,
        selected_action=selected,
        reason="highest_severity_then_stable_action_order",
    )
