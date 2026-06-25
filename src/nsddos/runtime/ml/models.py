"""Typed deterministic ML models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from nsddos.runtime.domain.versions import CONTRACT_VERSION, SCHEMA_VERSION


@dataclass(frozen=True)
class MLFeatureVector:
    packet_rate: float
    byte_rate: float
    connection_rate: float
    syn_rate: float
    udp_rate: float
    icmp_rate: float
    entropy_score: float
    packet_variance: float
    flow_duration: float
    attack_frequency: float
    mitigation_success_rate: float
    source_reputation_score: float

    def values(self) -> tuple[float, ...]:
        return (
            self.packet_rate,
            self.byte_rate,
            self.connection_rate,
            self.syn_rate,
            self.udp_rate,
            self.icmp_rate,
            self.entropy_score,
            self.packet_variance,
            self.flow_duration,
            self.attack_frequency,
            self.mitigation_success_rate,
            self.source_reputation_score,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_rate": self.packet_rate,
            "byte_rate": self.byte_rate,
            "connection_rate": self.connection_rate,
            "syn_rate": self.syn_rate,
            "udp_rate": self.udp_rate,
            "icmp_rate": self.icmp_rate,
            "entropy_score": self.entropy_score,
            "packet_variance": self.packet_variance,
            "flow_duration": self.flow_duration,
            "attack_frequency": self.attack_frequency,
            "mitigation_success_rate": self.mitigation_success_rate,
            "source_reputation_score": self.source_reputation_score,
        }


@dataclass(frozen=True)
class MLDatasetRow:
    row_id: str
    attack_label: bool
    attack_type: str
    policy_action: str
    mitigation_success: bool
    confidence_score: float
    feature_vector: MLFeatureVector
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "attack_label": self.attack_label,
            "attack_type": self.attack_type,
            "policy_action": self.policy_action,
            "mitigation_success": self.mitigation_success,
            "confidence_score": self.confidence_score,
            "feature_vector": self.feature_vector.to_dict(),
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class MLDatasetSnapshot:
    dataset_id: str
    rows: tuple[MLDatasetRow, ...] = field(default_factory=tuple)
    row_count: int = 0
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "rows": [item.to_dict() for item in self.rows],
            "row_count": self.row_count,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class MLBaselineState:
    average_packet_rate: float
    average_traffic_volume: float
    average_connection_rate: float
    average_entropy_score: float
    protocol_baseline: tuple[tuple[str, float], ...] = field(default_factory=tuple)
    flow_baseline: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "average_packet_rate": self.average_packet_rate,
            "average_traffic_volume": self.average_traffic_volume,
            "average_connection_rate": self.average_connection_rate,
            "average_entropy_score": self.average_entropy_score,
            "protocol_baseline": list(self.protocol_baseline),
            "flow_baseline": self.flow_baseline,
        }


@dataclass(frozen=True)
class MLTrainingState:
    model_id: str
    model_family: str
    model_version: str
    attack_threshold: float
    type_centroids: tuple[tuple[str, tuple[float, ...]], ...] = field(
        default_factory=tuple
    )
    feature_weights: tuple[float, ...] = field(default_factory=tuple)
    trained_row_count: int = 0
    trained_at: str = ""

    def centroid_map(self) -> dict[str, tuple[float, ...]]:
        return {key: value for key, value in self.type_centroids}

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_family": self.model_family,
            "model_version": self.model_version,
            "attack_threshold": self.attack_threshold,
            "type_centroids": [
                [key, list(value)] for key, value in self.type_centroids
            ],
            "feature_weights": list(self.feature_weights),
            "trained_row_count": self.trained_row_count,
            "trained_at": self.trained_at,
        }


@dataclass(frozen=True)
class MLInferenceResult:
    attack_probability: float
    predicted_attack_type: str
    confidence_score: float
    classification_state: str
    margin_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "attack_probability": self.attack_probability,
            "predicted_attack_type": self.predicted_attack_type,
            "confidence_score": self.confidence_score,
            "classification_state": self.classification_state,
            "margin_score": self.margin_score,
        }


@dataclass(frozen=True)
class MLDriftState:
    drift_score: float
    feature_drift: float
    anomaly_drift: float
    attack_pattern_drift: float
    distribution_change: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "drift_score": self.drift_score,
            "feature_drift": self.feature_drift,
            "anomaly_drift": self.anomaly_drift,
            "attack_pattern_drift": self.attack_pattern_drift,
            "distribution_change": self.distribution_change,
        }


@dataclass(frozen=True)
class MLEvaluationMetrics:
    precision: float
    recall: float
    false_positive_rate: float
    false_negative_rate: float
    confidence_quality: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "precision": self.precision,
            "recall": self.recall,
            "false_positive_rate": self.false_positive_rate,
            "false_negative_rate": self.false_negative_rate,
            "confidence_quality": self.confidence_quality,
        }


@dataclass(frozen=True)
class MLFeedbackState:
    mitigation_success_rate: float
    false_positive_score: float
    failed_mitigation_score: float
    retraining_frequency: int
    total_feedback_events: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "mitigation_success_rate": self.mitigation_success_rate,
            "false_positive_score": self.false_positive_score,
            "failed_mitigation_score": self.failed_mitigation_score,
            "retraining_frequency": self.retraining_frequency,
            "total_feedback_events": self.total_feedback_events,
        }


@dataclass(frozen=True)
class MLDiagnostics:
    model_accuracy_metrics: MLEvaluationMetrics
    drift_metrics: MLDriftState
    retraining_frequency: int
    false_positive_diagnostics: float
    anomaly_score_trend: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_accuracy_metrics": self.model_accuracy_metrics.to_dict(),
            "drift_metrics": self.drift_metrics.to_dict(),
            "retraining_frequency": self.retraining_frequency,
            "false_positive_diagnostics": self.false_positive_diagnostics,
            "anomaly_score_trend": self.anomaly_score_trend,
        }


@dataclass(frozen=True)
class MLDetectionEvaluation:
    model_id: str
    attack_probability: float
    predicted_attack_type: str
    confidence_score: float
    anomaly_score: float
    drift_score: float
    false_positive_score: float
    retraining_required: bool
    model_version: str
    timestamp: datetime
    feature_vector: MLFeatureVector
    dataset: MLDatasetSnapshot
    training_state: MLTrainingState
    inference: MLInferenceResult
    baseline: MLBaselineState
    drift: MLDriftState
    evaluation_metrics: MLEvaluationMetrics
    feedback_state: MLFeedbackState
    diagnostics: MLDiagnostics
    schema_version: str = SCHEMA_VERSION
    contract_version: str = CONTRACT_VERSION
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract_version": self.contract_version,
            "created_at": self.created_at,
            "model_id": self.model_id,
            "attack_probability": self.attack_probability,
            "predicted_attack_type": self.predicted_attack_type,
            "confidence_score": self.confidence_score,
            "anomaly_score": self.anomaly_score,
            "drift_score": self.drift_score,
            "false_positive_score": self.false_positive_score,
            "retraining_required": self.retraining_required,
            "model_version": self.model_version,
            "timestamp": self.timestamp.isoformat(),
            "feature_vector": self.feature_vector.to_dict(),
            "dataset": self.dataset.to_dict(),
            "training_state": self.training_state.to_dict(),
            "inference": self.inference.to_dict(),
            "baseline": self.baseline.to_dict(),
            "drift": self.drift.to_dict(),
            "evaluation_metrics": self.evaluation_metrics.to_dict(),
            "feedback_state": self.feedback_state.to_dict(),
            "diagnostics": self.diagnostics.to_dict(),
        }
