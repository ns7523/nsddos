"""ML persistence."""

from __future__ import annotations

from typing import Any

from nsddos.constants import RUNTIME_DIR
from nsddos.runtime.ml.models import (
    MLDatasetRow,
    MLDatasetSnapshot,
    MLDetectionEvaluation,
    MLEvaluationMetrics,
    MLFeatureVector,
    MLFeedbackState,
    MLTrainingState,
)
from nsddos.runtime.persistence import atomic_write_json, read_json_checked, recover_json

ML_DIR = RUNTIME_DIR / "ml"
LATEST_PATH = ML_DIR / "latest.json"
MODEL_PATH = ML_DIR / "model.json"
DATASET_PATH = ML_DIR / "dataset.json"
METRICS_PATH = ML_DIR / "metrics.json"
FEEDBACK_PATH = ML_DIR / "feedback.json"


def _feature_vector(payload: dict[str, Any]) -> MLFeatureVector:
    return MLFeatureVector(
        packet_rate=float(payload.get("packet_rate", 0.0)),
        byte_rate=float(payload.get("byte_rate", 0.0)),
        connection_rate=float(payload.get("connection_rate", 0.0)),
        syn_rate=float(payload.get("syn_rate", 0.0)),
        udp_rate=float(payload.get("udp_rate", 0.0)),
        icmp_rate=float(payload.get("icmp_rate", 0.0)),
        entropy_score=float(payload.get("entropy_score", 0.0)),
        packet_variance=float(payload.get("packet_variance", 0.0)),
        flow_duration=float(payload.get("flow_duration", 0.0)),
        attack_frequency=float(payload.get("attack_frequency", 0.0)),
        mitigation_success_rate=float(payload.get("mitigation_success_rate", 0.0)),
        source_reputation_score=float(payload.get("source_reputation_score", 0.0)),
    )


def load_dataset() -> MLDatasetSnapshot | None:
    payload = recover_json(DATASET_PATH, {})
    if not payload:
        return None
    rows = tuple(
        MLDatasetRow(
            row_id=str(item.get("row_id", "")),
            attack_label=bool(item.get("attack_label", False)),
            attack_type=str(item.get("attack_type", "normal")),
            policy_action=str(item.get("policy_action", "alert_only")),
            mitigation_success=bool(item.get("mitigation_success", False)),
            confidence_score=float(item.get("confidence_score", 0.0)),
            feature_vector=_feature_vector(item.get("feature_vector", {})),
            timestamp=str(item.get("timestamp", "")),
        )
        for item in payload.get("rows", [])
        if isinstance(item, dict)
    )
    return MLDatasetSnapshot(
        dataset_id=str(payload.get("dataset_id", "")),
        rows=rows,
        row_count=int(payload.get("row_count", len(rows))),
        updated_at=str(payload.get("updated_at", "")),
    )


def load_model() -> MLTrainingState | None:
    payload = recover_json(MODEL_PATH, {})
    if not payload or not payload.get("model_id"):
        return None
    return MLTrainingState(
        model_id=str(payload.get("model_id", "")),
        model_family=str(payload.get("model_family", "random_forest_style")),
        model_version=str(payload.get("model_version", "")),
        attack_threshold=float(payload.get("attack_threshold", 0.5)),
        type_centroids=tuple(
            (str(item[0]), tuple(float(value) for value in item[1]))
            for item in payload.get("type_centroids", [])
            if isinstance(item, list) and len(item) == 2
        ),
        feature_weights=tuple(float(item) for item in payload.get("feature_weights", [])),
        trained_row_count=int(payload.get("trained_row_count", 0)),
        trained_at=str(payload.get("trained_at", "")),
    )


def load_metrics() -> MLEvaluationMetrics | None:
    payload = recover_json(METRICS_PATH, {})
    if not payload:
        return None
    return MLEvaluationMetrics(
        precision=float(payload.get("precision", 0.0)),
        recall=float(payload.get("recall", 0.0)),
        false_positive_rate=float(payload.get("false_positive_rate", 0.0)),
        false_negative_rate=float(payload.get("false_negative_rate", 0.0)),
        confidence_quality=float(payload.get("confidence_quality", 0.0)),
    )


def load_feedback() -> MLFeedbackState | None:
    payload = recover_json(FEEDBACK_PATH, {})
    if not payload:
        return None
    return MLFeedbackState(
        mitigation_success_rate=float(payload.get("mitigation_success_rate", 0.0)),
        false_positive_score=float(payload.get("false_positive_score", 0.0)),
        failed_mitigation_score=float(payload.get("failed_mitigation_score", 0.0)),
        retraining_frequency=int(payload.get("retraining_frequency", 0)),
        total_feedback_events=int(payload.get("total_feedback_events", 0)),
    )


def persist_latest(evaluation: MLDetectionEvaluation) -> None:
    ML_DIR.mkdir(parents=True, exist_ok=True)
    payload = evaluation.to_dict()
    stamp = evaluation.timestamp.strftime("%Y%m%dT%H%M%S%fZ")
    atomic_write_json(ML_DIR / f"ml-{stamp}.json", payload)
    atomic_write_json(LATEST_PATH, payload)


def persist_model(model: MLTrainingState) -> None:
    ML_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_json(MODEL_PATH, model.to_dict())


def persist_dataset(dataset: MLDatasetSnapshot) -> None:
    ML_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_json(DATASET_PATH, dataset.to_dict())


def persist_metrics(metrics: MLEvaluationMetrics) -> None:
    ML_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_json(METRICS_PATH, metrics.to_dict())


def persist_feedback(feedback: MLFeedbackState) -> None:
    ML_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_json(FEEDBACK_PATH, feedback.to_dict())


def latest_ml_evaluation() -> dict[str, Any]:
    if not LATEST_PATH.exists():
        return {}
    return read_json_checked(LATEST_PATH)
