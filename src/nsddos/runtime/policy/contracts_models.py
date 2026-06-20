"""Typed dynamic policy models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from nsddos.runtime.domain.versions import CONTRACT_VERSION, SCHEMA_VERSION


@dataclass(frozen=True)
class PolicyRule:
    rule_id: str
    attack_type: str
    recommended_action: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "attack_type": self.attack_type,
            "recommended_action": self.recommended_action,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class PolicyConditionResult:
    repeated_attack_frequency: int
    repeated_source_ip: bool
    repeated_subnet_attacks: bool
    confidence_threshold_met: bool
    freshness_degraded: bool
    replay_restricted: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "repeated_attack_frequency": self.repeated_attack_frequency,
            "repeated_source_ip": self.repeated_source_ip,
            "repeated_subnet_attacks": self.repeated_subnet_attacks,
            "confidence_threshold_met": self.confidence_threshold_met,
            "freshness_degraded": self.freshness_degraded,
            "replay_restricted": self.replay_restricted,
        }


@dataclass(frozen=True)
class PolicyPriority:
    level: str
    score: int

    def to_dict(self) -> dict[str, Any]:
        return {"level": self.level, "score": self.score}


@dataclass(frozen=True)
class PolicyThresholdState:
    attack_frequency: int
    source_reputation_score: float
    historical_confidence_score: float
    mitigation_success_rate: float
    threshold_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "attack_frequency": self.attack_frequency,
            "source_reputation_score": self.source_reputation_score,
            "historical_confidence_score": self.historical_confidence_score,
            "mitigation_success_rate": self.mitigation_success_rate,
            "threshold_score": self.threshold_score,
        }


@dataclass(frozen=True)
class PolicyHistoryEntry:
    policy_id: str
    attack_type: str
    source_ip: str
    source_subnet: str
    recommended_action: str
    confidence_score: float
    escalation_level: int
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "attack_type": self.attack_type,
            "source_ip": self.source_ip,
            "source_subnet": self.source_subnet,
            "recommended_action": self.recommended_action,
            "confidence_score": self.confidence_score,
            "escalation_level": self.escalation_level,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class PolicyLearningState:
    attack_signature_counts: dict[str, int] = field(default_factory=dict)
    source_ip_counts: dict[str, int] = field(default_factory=dict)
    subnet_counts: dict[str, int] = field(default_factory=dict)
    mitigation_success_rate: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "attack_signature_counts": dict(sorted(self.attack_signature_counts.items())),
            "source_ip_counts": dict(sorted(self.source_ip_counts.items())),
            "subnet_counts": dict(sorted(self.subnet_counts.items())),
            "mitigation_success_rate": dict(sorted(self.mitigation_success_rate.items())),
        }


@dataclass(frozen=True)
class PolicyConflictResolution:
    candidates: tuple[str, ...]
    selected_action: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidates": list(self.candidates),
            "selected_action": self.selected_action,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class PolicyRollbackState:
    rollback_id: str
    restored_policy_id: str
    restored_action: str
    restored_escalation_level: int
    restored_threshold_score: float
    timestamp: str
    restored: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "rollback_id": self.rollback_id,
            "restored_policy_id": self.restored_policy_id,
            "restored_action": self.restored_action,
            "restored_escalation_level": self.restored_escalation_level,
            "restored_threshold_score": self.restored_threshold_score,
            "timestamp": self.timestamp,
            "restored": self.restored,
        }


@dataclass(frozen=True)
class PolicyDiagnostics:
    decision_latency_ms: float
    conflict_count: int
    escalation_level: int
    rollback_ready: bool
    threshold_drift: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_latency_ms": self.decision_latency_ms,
            "conflict_count": self.conflict_count,
            "escalation_level": self.escalation_level,
            "rollback_ready": self.rollback_ready,
            "threshold_drift": self.threshold_drift,
        }


@dataclass(frozen=True)
class PolicyEvaluation:
    policy_id: str
    attack_type: str
    source_ip: str
    attack_frequency: int
    confidence_score: float
    risk_level: str
    recommended_action: str
    escalation_level: int
    threshold_score: float
    policy_generation: str
    timestamp: datetime
    source_subnet: str = ""
    priority: PolicyPriority = field(default_factory=lambda: PolicyPriority("LOW", 0))
    rule: PolicyRule = field(default_factory=lambda: PolicyRule("", "normal", "alert_only", ""))
    conditions: PolicyConditionResult = field(default_factory=lambda: PolicyConditionResult(0, False, False, False, False, False))
    threshold_state: PolicyThresholdState = field(default_factory=lambda: PolicyThresholdState(0, 0.0, 0.0, 1.0, 0.0))
    conflict_resolution: PolicyConflictResolution = field(default_factory=lambda: PolicyConflictResolution(tuple(), "alert_only", ""))
    diagnostics: PolicyDiagnostics = field(default_factory=lambda: PolicyDiagnostics(0.0, 0, 0, False, 0.0))
    schema_version: str = SCHEMA_VERSION
    contract_version: str = CONTRACT_VERSION
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract_version": self.contract_version,
            "created_at": self.created_at,
            "policy_id": self.policy_id,
            "attack_type": self.attack_type,
            "source_ip": self.source_ip,
            "source_subnet": self.source_subnet,
            "attack_frequency": self.attack_frequency,
            "confidence_score": self.confidence_score,
            "risk_level": self.risk_level,
            "recommended_action": self.recommended_action,
            "escalation_level": self.escalation_level,
            "threshold_score": self.threshold_score,
            "policy_generation": self.policy_generation,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.to_dict(),
            "rule": self.rule.to_dict(),
            "conditions": self.conditions.to_dict(),
            "threshold_state": self.threshold_state.to_dict(),
            "conflict_resolution": self.conflict_resolution.to_dict(),
            "diagnostics": self.diagnostics.to_dict(),
        }
