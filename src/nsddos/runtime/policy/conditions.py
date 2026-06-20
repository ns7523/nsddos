"""Dynamic policy condition checks."""

from __future__ import annotations

from nsddos.runtime.policy.contracts_models import PolicyConditionResult, PolicyHistoryEntry


def evaluate_conditions(
    *,
    attack_type: str,
    source_ip: str,
    source_subnet: str,
    confidence_score: float,
    freshness_degraded: bool,
    replay_mode: bool,
    history: tuple[PolicyHistoryEntry, ...],
) -> PolicyConditionResult:
    repeated_attack_frequency = len([item for item in history if item.attack_type == attack_type and item.source_ip == source_ip]) + 1
    repeated_source_ip = any(item.source_ip == source_ip for item in history)
    repeated_subnet_attacks = bool(source_subnet) and any(item.source_subnet == source_subnet for item in history)
    return PolicyConditionResult(
        repeated_attack_frequency=repeated_attack_frequency,
        repeated_source_ip=repeated_source_ip,
        repeated_subnet_attacks=repeated_subnet_attacks,
        confidence_threshold_met=confidence_score >= 0.5,
        freshness_degraded=freshness_degraded,
        replay_restricted=replay_mode,
    )
