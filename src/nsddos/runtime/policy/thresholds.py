"""Dynamic threshold calculations."""

from __future__ import annotations

from nsddos.runtime.policy.contracts_models import PolicyLearningState, PolicyThresholdState


def calculate_thresholds(
    *,
    attack_frequency: int,
    source_ip: str,
    attack_type: str,
    confidence_score: float,
    learning_state: PolicyLearningState,
) -> PolicyThresholdState:
    source_reputation = min(1.0, learning_state.source_ip_counts.get(source_ip, 0) / 4.0)
    historical_confidence = confidence_score
    success_rate = float(learning_state.mitigation_success_rate.get(attack_type, 1.0))
    threshold_score = min(1.0, (attack_frequency * 0.25) + (source_reputation * 0.2) + (historical_confidence * 0.35) + (success_rate * 0.2))
    return PolicyThresholdState(
        attack_frequency=attack_frequency,
        source_reputation_score=source_reputation,
        historical_confidence_score=historical_confidence,
        mitigation_success_rate=success_rate,
        threshold_score=threshold_score,
    )
