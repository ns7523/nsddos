"""Detection registry for diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field

from nsddos.runtime.detection.thresholds import ANOMALY_THRESHOLDS, DEFAULT_BASELINES, SCORING_WEIGHTS, SIGNATURE_THRESHOLDS


@dataclass(frozen=True)
class DetectionRegistry:
    attacks: tuple[str, ...] = tuple(sorted(SIGNATURE_THRESHOLDS))
    anomalies: tuple[str, ...] = tuple(sorted(ANOMALY_THRESHOLDS))
    features: tuple[str, ...] = (
        "packet_rate",
        "byte_rate",
        "connection_rate",
        "syn_rate",
        "ack_rate",
        "udp_rate",
        "icmp_rate",
        "entropy_score",
        "source_ip_cardinality",
        "destination_port_distribution",
        "connection_burst_factor",
        "packet_size_variance",
        "flow_duration",
    )
    score_weights: dict[str, float] = field(default_factory=lambda: dict(SCORING_WEIGHTS))
    baselines: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_BASELINES))

    def to_dict(self) -> dict[str, object]:
        return {
            "attacks": list(self.attacks),
            "anomalies": list(self.anomalies),
            "features": list(self.features),
            "score_weights": dict(self.score_weights),
            "baselines": dict(self.baselines),
            "signature_thresholds": SIGNATURE_THRESHOLDS,
            "anomaly_thresholds": ANOMALY_THRESHOLDS,
        }


def default_detection_registry() -> DetectionRegistry:
    return DetectionRegistry()
