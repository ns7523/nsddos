"""Static baseline policy rules."""

from __future__ import annotations

from nsddos.runtime.detection.models import DetectionEvaluation
from nsddos.runtime.policy.contracts_models import PolicyRule


def baseline_rule(detection: DetectionEvaluation) -> PolicyRule:
    if not detection.attack_detected or detection.confidence_score < 0.5:
        return PolicyRule(
            "policy_alert_only",
            detection.attack_type,
            "alert_only",
            "normal_or_low_confidence",
        )
    mapping = {
        "syn_flood": ("policy_rate_limit", "rate_limit", "baseline_syn_response"),
        "udp_flood": ("policy_drop_traffic", "drop_traffic", "baseline_udp_response"),
        "icmp_flood": ("policy_block_ip", "block_ip", "baseline_icmp_response"),
        "http_flood": ("policy_rate_limit", "rate_limit", "baseline_http_response"),
        "slowloris": (
            "policy_connection_reset",
            "connection_reset",
            "baseline_slowloris_response",
        ),
        "connection_exhaustion": (
            "policy_quarantine_host",
            "quarantine_host",
            "baseline_connection_quarantine",
        ),
    }
    policy_id, action, reason = mapping.get(
        detection.attack_type,
        ("policy_alert_only", "alert_only", "baseline_default_alert"),
    )
    return PolicyRule(policy_id, detection.attack_type, action, reason)
