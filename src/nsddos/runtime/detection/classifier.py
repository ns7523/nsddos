"""Rule-based attack classification."""

from __future__ import annotations

from nsddos.runtime.detection.models import (
    AnomalyResult,
    AttackClassification,
    RiskAssessment,
    SignatureMatch,
)


PRIORITY = (
    "syn_flood",
    "udp_flood",
    "icmp_flood",
    "http_flood",
    "slowloris",
    "connection_exhaustion",
    "port_scanning",
    "volumetric_anomaly",
)


def classify_attack(
    signatures: tuple[SignatureMatch, ...],
    anomalies: tuple[AnomalyResult, ...],
    risk: RiskAssessment,
) -> AttackClassification:
    """Classify attack type and severity."""
    matched_names = tuple(item.name for item in signatures if item.matched)
    anomaly_names = tuple(item.name for item in anomalies if item.triggered)
    attack_type = "normal"
    for name in PRIORITY:
        if name in matched_names:
            attack_type = name
            break
    if attack_type == "normal" and any(item.triggered for item in anomalies):
        attack_type = "volumetric_anomaly"
    if attack_type == "normal":
        severity = "normal"
        attack_detected = False
    elif risk.risk_level == "CRITICAL":
        severity = "critical_attack"
        attack_detected = True
    elif risk.risk_level in {"HIGH", "MEDIUM"}:
        severity = "attack"
        attack_detected = True
    else:
        severity = "suspicious"
        attack_detected = True
    return AttackClassification(
        attack_type=attack_type,
        severity=severity,
        attack_detected=attack_detected,
        confidence_score=risk.confidence_score,
        signature_score=risk.signature_score,
        anomaly_score=risk.anomaly_score,
        traffic_intensity_score=risk.traffic_intensity_score,
        matched_signatures=matched_names,
        triggered_anomalies=anomaly_names,
    )
