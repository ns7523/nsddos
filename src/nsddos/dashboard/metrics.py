"""Dashboard metrics aggregation."""

from __future__ import annotations

from nsddos.dashboard.contracts import DashboardSourceBundle, MetricsState


def build_metrics_state(sources: DashboardSourceBundle) -> MetricsState:
    """Aggregate throughput and event frequencies."""
    stream = sources.streaming
    ml = sources.ml
    detection = sources.detection
    mitigation = sources.mitigation
    packet_throughput = float(
        ml.get("feature_vector", {}).get("packet_rate", 0.0)
    ) or float(stream.get("aggregation", {}).get("packet_total", 0.0))
    byte_throughput = float(
        ml.get("feature_vector", {}).get("byte_rate", 0.0)
    ) or float(stream.get("aggregation", {}).get("byte_total", 0.0))
    attack_frequency = int(bool(detection.get("attack_detected", False))) + sum(
        1
        for item in sources.policy_history
        if item.get("attack_type") not in {"", "normal"}
    )
    detection_frequency = int(bool(detection.get("classification_generation")))
    mitigation_frequency = int(
        bool(
            mitigation.get("mitigation_action")
            and mitigation.get("mitigation_action") != "alert_only"
        )
    )
    return MetricsState(
        packet_throughput=packet_throughput,
        byte_throughput=byte_throughput,
        attack_frequency=attack_frequency,
        detection_frequency=detection_frequency,
        mitigation_frequency=mitigation_frequency,
    )
