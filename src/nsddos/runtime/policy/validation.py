"""Dynamic policy validation."""

from __future__ import annotations

from nsddos.runtime.policy.actions import allowed_actions
from nsddos.runtime.policy.contracts_models import PolicyEvaluation, PolicyHistoryEntry, PolicyRollbackState


def validate_policy_evaluation(evaluation: PolicyEvaluation) -> list[str]:
    errors: list[str] = []
    if evaluation.recommended_action not in allowed_actions():
        errors.append("invalid_recommended_action")
    if evaluation.escalation_level < 0 or evaluation.escalation_level > 4:
        errors.append("invalid_escalation_level")
    if not 0.0 <= evaluation.threshold_score <= 1.0:
        errors.append("invalid_threshold_score")
    if not evaluation.policy_id:
        errors.append("malformed_policy_state")
    if not evaluation.policy_generation:
        errors.append("missing_policy_generation")
    return errors


def validate_policy_history(entries: tuple[PolicyHistoryEntry, ...]) -> list[str]:
    errors: list[str] = []
    for item in entries:
        if item.recommended_action not in allowed_actions():
            errors.append("malformed_policy_history")
        if item.escalation_level < 0:
            errors.append("invalid_escalation_level")
    return sorted(set(errors))


def validate_policy_rollback(state: PolicyRollbackState) -> list[str]:
    errors: list[str] = []
    if state.restored_action not in allowed_actions():
        errors.append("rollback_failure")
    if state.restored_escalation_level < 0 or state.restored_escalation_level > 4:
        errors.append("invalid_escalation_level")
    return sorted(set(errors))
