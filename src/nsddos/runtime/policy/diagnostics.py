"""Policy diagnostics."""

from __future__ import annotations

from nsddos.runtime.policy.contracts_models import (
    PolicyDiagnostics,
    PolicyEvaluation,
    PolicyHistoryEntry,
)


def build_policy_diagnostics(
    *,
    history: tuple[PolicyHistoryEntry, ...],
    escalation_level: int,
    threshold_score: float,
    previous_threshold_score: float,
    decision_latency_ms: float,
    conflict_count: int,
) -> PolicyDiagnostics:
    return PolicyDiagnostics(
        decision_latency_ms=decision_latency_ms,
        conflict_count=conflict_count,
        escalation_level=escalation_level,
        rollback_ready=len(history) > 0,
        threshold_drift=threshold_score - previous_threshold_score,
    )


def explain_policy(payload: PolicyEvaluation) -> dict[str, object]:
    data = payload.to_dict()
    data["persistence"] = "latest_plus_history_plus_learning"
    data["mode"] = "dry_run_dynamic_policy"
    return data
