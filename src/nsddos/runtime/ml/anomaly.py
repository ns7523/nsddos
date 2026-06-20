"""Deterministic anomaly scoring."""

from __future__ import annotations

from nsddos.runtime.ml.models import MLBaselineState, MLFeatureVector


def anomaly_score(features: MLFeatureVector, baseline: MLBaselineState) -> tuple[float, float]:
    packet_delta = abs(features.packet_rate - baseline.average_packet_rate) / max(baseline.average_packet_rate, 1.0)
    byte_delta = abs(features.byte_rate - baseline.average_traffic_volume) / max(baseline.average_traffic_volume, 1.0)
    connection_delta = abs(features.connection_rate - baseline.average_connection_rate) / max(baseline.average_connection_rate, 1.0)
    entropy_delta = abs(features.entropy_score - baseline.average_entropy_score)
    score = min(1.0, (packet_delta * 0.35) + (byte_delta * 0.25) + (connection_delta * 0.25) + (entropy_delta * 0.15))
    confidence = min(1.0, 0.5 + (score / 2.0))
    return score, confidence
