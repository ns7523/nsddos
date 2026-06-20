"""Mitigation validation."""

from __future__ import annotations

import ipaddress

from nsddos.runtime.mitigation.contracts import ENFORCEMENT_STEP_STATUSES, EXECUTION_RESULTS, MITIGATION_ACTIONS, MITIGATION_STATUSES, POLICY_NAMES, REQUIRES_SUBNET, REQUIRES_TARGET_IP, STRATEGY_NAMES
from nsddos.runtime.mitigation.models import MitigationEvaluation


def _valid_ip(value: str) -> bool:
    if not value:
        return False
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


def _valid_subnet(value: str) -> bool:
    if not value:
        return False
    try:
        ipaddress.ip_network(value, strict=False)
    except ValueError:
        return False
    return True


def validate_mitigation_evaluation(evaluation: MitigationEvaluation) -> list[str]:
    errors: list[str] = []
    if evaluation.mitigation_action not in MITIGATION_ACTIONS:
        errors.append("invalid_mitigation_action")
    if evaluation.mitigation_status not in MITIGATION_STATUSES:
        errors.append("invalid_mitigation_status")
    if evaluation.execution_result not in EXECUTION_RESULTS:
        errors.append("invalid_execution_result")
    if evaluation.policy.policy_name not in POLICY_NAMES:
        errors.append("invalid_policy_selection")
    if evaluation.strategy.strategy_name not in STRATEGY_NAMES:
        errors.append("invalid_strategy_selection")
    if not 0.0 <= evaluation.confidence_score <= 1.0:
        errors.append("confidence_score_out_of_range")
    if evaluation.mitigation_action in REQUIRES_TARGET_IP and not _valid_ip(evaluation.target_ip):
        errors.append("missing_target_ip")
    if evaluation.mitigation_action in REQUIRES_SUBNET and not _valid_subnet(evaluation.target_subnet):
        errors.append("malformed_target_subnet")
    if evaluation.mitigation_action == "alert_only" and evaluation.target_ip:
        errors.append("unexpected_target_ip")
    if evaluation.mitigation_required != (evaluation.mitigation_action != "alert_only"):
        errors.append("mitigation_required_mismatch")
    if evaluation.action_payload.action_type != evaluation.mitigation_action:
        errors.append("action_payload_mismatch")
    if evaluation.controller_payload is None and evaluation.mitigation_action != "alert_only":
        errors.append("invalid_execution_payload")
    if evaluation.controller_payload is not None:
        flow_rule = evaluation.controller_payload.flow_rule
        if flow_rule.action_type != evaluation.mitigation_action:
            errors.append("malformed_flow_rule")
        if flow_rule.match_value != (evaluation.target_subnet or evaluation.target_ip):
            errors.append("flow_rule_target_mismatch")
    if evaluation.controller_mutation_status not in ENFORCEMENT_STEP_STATUSES:
        errors.append("invalid_controller_mutation_status")
    if evaluation.ovs_insertion_status not in ENFORCEMENT_STEP_STATUSES:
        errors.append("invalid_ovs_insertion_status")
    if evaluation.flow_verification_status not in ENFORCEMENT_STEP_STATUSES:
        errors.append("invalid_flow_verification_status")
    if evaluation.traffic_block_status not in ENFORCEMENT_STEP_STATUSES:
        errors.append("invalid_traffic_block_status")
    if not evaluation.mitigation_hash:
        errors.append("mitigation_hash_missing")
    if not evaluation.mitigation_generation:
        errors.append("mitigation_generation_missing")
    return errors
