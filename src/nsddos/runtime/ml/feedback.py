"""Deterministic mitigation feedback collection."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.ml.models import MLFeedbackState


def build_feedback_state(
    policy_history_payload: dict[str, Any],
    mitigation_payload: dict[str, Any],
) -> MLFeedbackState:
    entries = policy_history_payload.get("entries", [])
    if not isinstance(entries, list):
        entries = []
    total = len(entries)
    escalated = sum(
        1
        for item in entries
        if isinstance(item, dict) and int(item.get("escalation_level", 0)) > 1
    )
    alert_only = sum(
        1
        for item in entries
        if isinstance(item, dict)
        and str(item.get("recommended_action", "")) == "alert_only"
    )
    mitigation_action = str(mitigation_payload.get("mitigation_action", "alert_only"))
    mitigation_success = 0.0 if mitigation_action == "alert_only" else 1.0
    success_rate = ((total - alert_only) / total) if total else mitigation_success
    false_positive_score = (alert_only / total) if total else 0.0
    failed_mitigation_score = max(0.0, 1.0 - success_rate)
    return MLFeedbackState(
        mitigation_success_rate=max(0.0, min(1.0, success_rate)),
        false_positive_score=max(0.0, min(1.0, false_positive_score)),
        failed_mitigation_score=max(0.0, min(1.0, failed_mitigation_score)),
        retraining_frequency=escalated,
        total_feedback_events=total,
    )
