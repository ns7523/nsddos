"""Deterministic ML feature engineering."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.detection.models import DetectionEvaluation
from nsddos.runtime.ml.models import MLFeatureVector, MLFeedbackState


def _numeric(flow: dict[str, Any], key: str) -> float:
    value = flow.get(key, 0.0)
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def extract_ml_features(
    telemetry: dict[str, Any],
    detection: DetectionEvaluation,
    feedback_state: MLFeedbackState,
    attack_frequency: float,
) -> MLFeatureVector:
    flows = telemetry.get("flows", [])
    if not isinstance(flows, list):
        flows = []
    packet_values = [_numeric(flow, "packets") for flow in flows if isinstance(flow, dict)]
    durations = [_numeric(flow, "duration") for flow in flows if isinstance(flow, dict)]
    protocol_volume = {"tcp": 0.0, "udp": 0.0, "icmp": 0.0}
    for flow in flows:
        if not isinstance(flow, dict):
            continue
        protocol = str(flow.get("protocol", "tcp")).lower()
        protocol_volume[protocol] = protocol_volume.get(protocol, 0.0) + _numeric(flow, "packets")
    packet_rate = detection.feature_vector.packet_rate
    byte_rate = detection.feature_vector.byte_rate
    connection_rate = detection.feature_vector.connection_rate
    mean_packets = sum(packet_values) / max(len(packet_values), 1)
    packet_variance = (
        sum((value - mean_packets) ** 2 for value in packet_values) / max(len(packet_values), 1)
        if packet_values
        else detection.feature_vector.packet_size_variance
    )
    flow_duration = sum(durations) / max(len(durations), 1) if durations else detection.feature_vector.flow_duration
    source_reputation = min(1.0, attack_frequency / 4.0)
    return MLFeatureVector(
        packet_rate=packet_rate,
        byte_rate=byte_rate,
        connection_rate=connection_rate,
        syn_rate=detection.feature_vector.syn_rate,
        udp_rate=detection.feature_vector.udp_rate,
        icmp_rate=detection.feature_vector.icmp_rate,
        entropy_score=detection.feature_vector.entropy_score,
        packet_variance=packet_variance,
        flow_duration=flow_duration,
        attack_frequency=attack_frequency,
        mitigation_success_rate=feedback_state.mitigation_success_rate,
        source_reputation_score=source_reputation,
    )
