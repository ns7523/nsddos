"""Detection validation."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.detection.contracts import (
    DETECTION_ATTACK_TYPES,
    DETECTION_RISK_LEVELS,
    DETECTION_STATES,
    DETECTION_STATUS,
    REQUIRED_TELEMETRY_FIELDS,
)
from nsddos.runtime.detection.models import DetectionEvaluation, FeatureVector


def validate_detection_telemetry(telemetry: dict[str, Any]) -> list[str]:
    errors = [
        f"missing:{field}"
        for field in REQUIRED_TELEMETRY_FIELDS
        if field not in telemetry
    ]
    flows = telemetry.get("flows", [])
    if not isinstance(flows, list):
        errors.append("invalid:flows")
    return errors


def validate_feature_vector(features: FeatureVector) -> list[str]:
    errors: list[str] = []
    numeric_fields = (
        features.packet_rate,
        features.byte_rate,
        features.connection_rate,
        features.syn_rate,
        features.ack_rate,
        features.udp_rate,
        features.icmp_rate,
        features.http_rate,
        features.partial_connection_rate,
        features.entropy_score,
        features.connection_burst_factor,
        features.packet_size_variance,
        features.flow_duration,
    )
    if any(value < 0 for value in numeric_fields):
        errors.append("invalid_feature_vector_values")
    return errors


def validate_detection_evaluation(evaluation: DetectionEvaluation) -> list[str]:
    errors = validate_feature_vector(evaluation.feature_vector)
    if evaluation.attack_type not in DETECTION_ATTACK_TYPES:
        errors.append("malformed_attack_type")
    if evaluation.classification.severity not in DETECTION_STATES:
        errors.append("inconsistent_classification_state")
    if evaluation.detection_status not in DETECTION_STATUS:
        errors.append("invalid_detection_status")
    if evaluation.risk_level not in DETECTION_RISK_LEVELS:
        errors.append("invalid_risk_level")
    if not 0.0 <= evaluation.confidence_score <= 1.0:
        errors.append("confidence_score_out_of_range")
    if not evaluation.evidence_hash:
        errors.append("missing_evidence_hash")
    if evaluation.classification.attack_detected != evaluation.attack_detected:
        errors.append("attack_detected_mismatch")
    if evaluation.classification.confidence_score != evaluation.confidence_score:
        errors.append("confidence_score_mismatch")
    if evaluation.classification.attack_type != evaluation.attack_type:
        errors.append("attack_type_mismatch")
    if evaluation.risk.confidence_score != evaluation.confidence_score:
        errors.append("scoring_mismatch")
    return errors
