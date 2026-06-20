"""Detection score helpers."""

from __future__ import annotations

from nsddos.runtime.detection.models import AnomalyResult, FeatureVector, SignatureMatch
from nsddos.runtime.detection.thresholds import SCORING_WEIGHTS


def signature_score(signatures: tuple[SignatureMatch, ...]) -> float:
    matched = [item.score for item in signatures if item.matched]
    return min(sum(matched), 4.0)


def anomaly_score(anomalies: tuple[AnomalyResult, ...]) -> float:
    triggered = [item.score for item in anomalies if item.triggered]
    return min(sum(triggered), 4.0)


def traffic_intensity_score(features: FeatureVector) -> float:
    packet_component = min(features.packet_rate / 1000.0, 2.0)
    byte_component = min(features.byte_rate / 1_000_000.0, 2.0)
    return min(packet_component + byte_component, 4.0)


def confidence_score(signature: float, anomaly: float, intensity: float) -> float:
    weighted = (
        signature * SCORING_WEIGHTS["signature"]
        + anomaly * SCORING_WEIGHTS["anomaly"]
        + intensity * SCORING_WEIGHTS["traffic_intensity"]
    )
    return max(0.0, min(weighted / 4.0, 1.0))
