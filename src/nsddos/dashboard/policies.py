"""Dashboard policy analytics."""

from __future__ import annotations

from nsddos.dashboard.contracts import DashboardSourceBundle, PolicyAnalytics


def build_policy_analytics(sources: DashboardSourceBundle) -> PolicyAnalytics:
    """Aggregate policy history."""
    history = sources.policy_history
    thresholds = [
        float(item.get("confidence_score", 0.0))
        for item in history
        if isinstance(item, dict)
    ]
    escalations = sum(1 for item in history if int(item.get("escalation_level", 0)) > 0)
    rollbacks = sum(
        1
        for result in sources.verification
        if result.get("name") == "policy_rollback_validation"
    )
    return PolicyAnalytics(
        policy_events=len(history),
        escalation_frequency=escalations,
        rollback_frequency=rollbacks,
        threshold_evolution=tuple(thresholds),
    )
