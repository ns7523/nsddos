"""Deterministic concept drift detection."""

from __future__ import annotations

from nsddos.runtime.ml.models import (
    MLBaselineState,
    MLDriftState,
    MLEvaluationMetrics,
    MLFeatureVector,
)


def detect_drift(
    features: MLFeatureVector,
    baseline: MLBaselineState,
    metrics: MLEvaluationMetrics,
    anomaly_score: float,
) -> MLDriftState:
    feature_drift = min(
        1.0,
        (
            abs(features.packet_rate - baseline.average_packet_rate)
            / max(baseline.average_packet_rate, 1.0)
            + abs(features.byte_rate - baseline.average_traffic_volume)
            / max(baseline.average_traffic_volume, 1.0)
            + abs(features.connection_rate - baseline.average_connection_rate)
            / max(baseline.average_connection_rate, 1.0)
        )
        / 3.0,
    )
    anomaly_drift = abs(anomaly_score - metrics.false_positive_rate)
    attack_pattern_drift = min(1.0, abs(features.attack_frequency - metrics.recall))
    distribution_change = min(
        1.0, abs(features.entropy_score - baseline.average_entropy_score)
    )
    score = min(
        1.0,
        (feature_drift * 0.4)
        + (anomaly_drift * 0.2)
        + (attack_pattern_drift * 0.2)
        + (distribution_change * 0.2),
    )
    return MLDriftState(
        drift_score=score,
        feature_drift=feature_drift,
        anomaly_drift=anomaly_drift,
        attack_pattern_drift=attack_pattern_drift,
        distribution_change=distribution_change,
    )
