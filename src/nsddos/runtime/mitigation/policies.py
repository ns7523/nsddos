"""Mitigation policy mapping."""

from __future__ import annotations

from nsddos.runtime.detection.models import DetectionEvaluation
from nsddos.runtime.mitigation.models import MitigationPolicyDecision


def evaluate_policy(detection: DetectionEvaluation) -> MitigationPolicyDecision:
    if not detection.attack_detected or detection.confidence_score < 0.5:
        return MitigationPolicyDecision("policy_alert_only", False, "alert_only", "low confidence or normal traffic")
    if detection.classification.severity == "critical_attack":
        return MitigationPolicyDecision("policy_isolate_subnet", True, "isolate_subnet", "critical attack requires subnet isolation")
    if detection.attack_type == "syn_flood" and detection.risk_level in {"HIGH", "CRITICAL"}:
        return MitigationPolicyDecision("policy_block_ip", True, "block_ip", "syn flood high-risk response")
    if detection.attack_type == "udp_flood" and detection.risk_level in {"MEDIUM", "HIGH", "CRITICAL"}:
        return MitigationPolicyDecision("policy_rate_limit", True, "rate_limit", "udp flood rate limiting")
    if detection.attack_type == "icmp_flood" and detection.risk_level in {"HIGH", "CRITICAL"}:
        return MitigationPolicyDecision("policy_drop_traffic", True, "drop_traffic", "icmp flood traffic drop")
    if detection.attack_type == "http_flood" and detection.risk_level in {"MEDIUM", "HIGH", "CRITICAL"}:
        return MitigationPolicyDecision("policy_rate_limit", True, "rate_limit", "http flood rate limiting")
    if detection.attack_type == "slowloris" and detection.risk_level in {"MEDIUM", "HIGH", "CRITICAL"}:
        return MitigationPolicyDecision("policy_connection_reset", True, "connection_reset", "slowloris connection reset")
    if detection.attack_type == "connection_exhaustion" and detection.risk_level in {"HIGH", "CRITICAL"}:
        return MitigationPolicyDecision("policy_quarantine_host", True, "quarantine_host", "connection exhaustion host quarantine")
    if detection.attack_type == "port_scanning" and detection.risk_level in {"MEDIUM", "HIGH", "CRITICAL"}:
        return MitigationPolicyDecision("policy_temporary_ban", True, "temporary_ban", "port scanning temporary ban")
    if detection.attack_type == "volumetric_anomaly" and detection.risk_level in {"MEDIUM", "HIGH", "CRITICAL"}:
        return MitigationPolicyDecision("policy_connection_reset", True, "connection_reset", "volumetric anomaly connection reset")
    return MitigationPolicyDecision("policy_alert_only", False, "alert_only", "no deterministic mitigation required")
