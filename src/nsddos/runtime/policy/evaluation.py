"""Policy evaluation assembly."""

from __future__ import annotations

from datetime import datetime

from nsddos.runtime.domain.identifiers import deterministic_id
from nsddos.runtime.policy.contracts_models import (
    PolicyConditionResult,
    PolicyConflictResolution,
    PolicyDiagnostics,
    PolicyEvaluation,
    PolicyPriority,
    PolicyRule,
    PolicyThresholdState,
)


def build_policy_evaluation(
    *,
    attack_type: str,
    source_ip: str,
    source_subnet: str,
    confidence_score: float,
    risk_level: str,
    recommended_action: str,
    escalation_level: int,
    threshold_state: PolicyThresholdState,
    priority: PolicyPriority,
    rule: PolicyRule,
    conditions: PolicyConditionResult,
    conflict_resolution: PolicyConflictResolution,
    diagnostics: PolicyDiagnostics,
    timestamp: datetime,
) -> PolicyEvaluation:
    generation = deterministic_id(
        "policy-generation",
        f"{attack_type}:{source_ip}:{recommended_action}:{timestamp.isoformat()}",
    )
    policy_id = deterministic_id(
        "policy",
        f"{attack_type}:{source_ip}:{escalation_level}:{threshold_state.threshold_score:.4f}",
    )
    return PolicyEvaluation(
        policy_id=policy_id,
        attack_type=attack_type,
        source_ip=source_ip,
        source_subnet=source_subnet,
        attack_frequency=threshold_state.attack_frequency,
        confidence_score=confidence_score,
        risk_level=risk_level,
        recommended_action=recommended_action,
        escalation_level=escalation_level,
        threshold_score=threshold_state.threshold_score,
        policy_generation=generation,
        timestamp=timestamp,
        priority=priority,
        rule=rule,
        conditions=conditions,
        threshold_state=threshold_state,
        conflict_resolution=conflict_resolution,
        diagnostics=diagnostics,
        created_at=timestamp.isoformat(),
    )
