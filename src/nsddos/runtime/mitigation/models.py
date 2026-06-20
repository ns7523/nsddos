"""Typed mitigation models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from nsddos.runtime.domain.versions import CONTRACT_VERSION, SCHEMA_VERSION


@dataclass(frozen=True)
class MitigationPolicyDecision:
    policy_name: str
    mitigation_required: bool
    selected_action: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_name": self.policy_name,
            "mitigation_required": self.mitigation_required,
            "selected_action": self.selected_action,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class MitigationStrategySelection:
    strategy_name: str
    action_type: str
    mode: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "action_type": self.action_type,
            "mode": self.mode,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class MitigationActionPayload:
    action_type: str
    target_ip: str = ""
    target_subnet: str = ""
    duration_seconds: int = 0
    bandwidth_mbps: int = 0
    packet_rate_limit: int = 0
    connection_limit: int = 0
    reset_connections: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "target_ip": self.target_ip,
            "target_subnet": self.target_subnet,
            "duration_seconds": self.duration_seconds,
            "bandwidth_mbps": self.bandwidth_mbps,
            "packet_rate_limit": self.packet_rate_limit,
            "connection_limit": self.connection_limit,
            "reset_connections": self.reset_connections,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class MitigationFlowRule:
    rule_id: str
    priority: int
    match_field: str
    match_value: str
    action_type: str
    duration_seconds: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "priority": self.priority,
            "match_field": self.match_field,
            "match_value": self.match_value,
            "action_type": self.action_type,
            "duration_seconds": self.duration_seconds,
        }


@dataclass(frozen=True)
class MitigationControllerPayload:
    controller_type: str
    provider_target: str
    flow_rule: MitigationFlowRule
    payload_hash: str
    command: str
    floodlight_payload: dict[str, Any] = field(default_factory=dict)
    ovs_flow: str = ""
    verification_matches: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "controller_type": self.controller_type,
            "provider_target": self.provider_target,
            "flow_rule": self.flow_rule.to_dict(),
            "payload_hash": self.payload_hash,
            "command": self.command,
            "floodlight_payload": self.floodlight_payload,
            "ovs_flow": self.ovs_flow,
            "verification_matches": self.verification_matches,
        }


@dataclass(frozen=True)
class MitigationEvidence:
    mitigation_hash: str
    mitigation_generation: str
    action_type: str
    target_ip: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "mitigation_hash": self.mitigation_hash,
            "mitigation_generation": self.mitigation_generation,
            "action_type": self.action_type,
            "target_ip": self.target_ip,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class MitigationEvaluation:
    mitigation_required: bool
    mitigation_action: str
    target_ip: str
    confidence_score: float
    mitigation_status: str
    execution_result: str
    mitigation_generation: str
    mitigation_hash: str
    timestamp: datetime
    attack_type: str
    risk_level: str
    target_subnet: str = ""
    detection_evidence_hash: str = ""
    policy: MitigationPolicyDecision = field(default_factory=lambda: MitigationPolicyDecision("", False, "alert_only", ""))
    strategy: MitigationStrategySelection = field(default_factory=lambda: MitigationStrategySelection("", "alert_only", "dry_run", ""))
    action_payload: MitigationActionPayload = field(default_factory=lambda: MitigationActionPayload("alert_only"))
    controller_payload: MitigationControllerPayload | None = None
    controller_mutation_status: str = "not_attempted"
    ovs_insertion_status: str = "not_attempted"
    flow_verification_status: str = "not_attempted"
    traffic_block_status: str = "not_attempted"
    enforcement_evidence: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION
    contract_version: str = CONTRACT_VERSION
    created_at: str = field(default="")

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "contract_version": self.contract_version,
            "created_at": self.created_at or self.timestamp.isoformat(),
            "mitigation_required": self.mitigation_required,
            "mitigation_action": self.mitigation_action,
            "target_ip": self.target_ip,
            "target_subnet": self.target_subnet,
            "confidence_score": self.confidence_score,
            "mitigation_status": self.mitigation_status,
            "execution_result": self.execution_result,
            "mitigation_generation": self.mitigation_generation,
            "mitigation_hash": self.mitigation_hash,
            "timestamp": self.timestamp.isoformat(),
            "attack_type": self.attack_type,
            "risk_level": self.risk_level,
            "detection_evidence_hash": self.detection_evidence_hash,
            "policy": self.policy.to_dict(),
            "strategy": self.strategy.to_dict(),
            "action_payload": self.action_payload.to_dict(),
            "controller_mutation_status": self.controller_mutation_status,
            "ovs_insertion_status": self.ovs_insertion_status,
            "flow_verification_status": self.flow_verification_status,
            "traffic_block_status": self.traffic_block_status,
            "enforcement_evidence": self.enforcement_evidence,
        }
        if self.controller_payload is not None:
            payload["controller_payload"] = self.controller_payload.to_dict()
        return payload
