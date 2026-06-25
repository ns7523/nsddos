"""Adaptive policy escalation."""

from __future__ import annotations

from nsddos.runtime.policy.contracts_models import (
    PolicyConditionResult,
    PolicyThresholdState,
)


def adaptive_action(
    baseline_action: str,
    *,
    conditions: PolicyConditionResult,
    threshold_state: PolicyThresholdState,
) -> tuple[str, int]:
    if (
        conditions.replay_restricted
        or conditions.freshness_degraded
        or not conditions.confidence_threshold_met
    ):
        return "alert_only", 0
    if conditions.repeated_attack_frequency >= 4:
        return "permanent_ban", 4
    if conditions.repeated_source_ip and threshold_state.threshold_score >= 0.35:
        return "block_ip", 2
    if conditions.repeated_subnet_attacks and threshold_state.threshold_score >= 0.55:
        return "isolate_subnet", 3
    if baseline_action == "alert_only":
        return "alert_only", 0
    return baseline_action, 1
