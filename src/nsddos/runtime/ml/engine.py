"""Deterministic ML engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from nsddos.runtime.detection import evaluate_detection
from nsddos.runtime.detection.models import DetectionEvaluation
from nsddos.runtime.ml.anomaly import anomaly_score
from nsddos.runtime.ml.baseline import build_baseline
from nsddos.runtime.ml.dataset import build_dataset_row, build_dataset_snapshot
from nsddos.runtime.ml.diagnostics import build_diagnostics
from nsddos.runtime.ml.drift import detect_drift
from nsddos.runtime.ml.evaluation import compute_evaluation_metrics
from nsddos.runtime.ml.features import extract_ml_features
from nsddos.runtime.ml.feedback import build_feedback_state
from nsddos.runtime.ml.inference import run_inference
from nsddos.runtime.ml.models import MLDetectionEvaluation, MLEvaluationMetrics
from nsddos.runtime.ml.persistence import (
    load_dataset,
    load_feedback,
    load_metrics,
    load_model,
    persist_dataset,
    persist_feedback,
    persist_latest,
    persist_metrics,
    persist_model,
)
from nsddos.runtime.ml.registry import retraining_required as registry_retraining_required
from nsddos.runtime.ml.training import retrain_model, train_model
from nsddos.runtime.ml.validation import validate_ml_evaluation

def _settings(config: dict[str, Any]) -> dict[str, Any]:
    top_level = config.get("ml", {})
    runtime = config.get("runtime", {}).get("ml", {})
    return {
        "enabled": bool(runtime.get("enabled", True)),
        "model_family": str(runtime.get("model_family", "random_forest_style")),
        "retrain_threshold": float(runtime.get("retrain_threshold", 0.35)),
        "dataset_limit": int(runtime.get("dataset_limit", 256)),
        "history_limit": int(runtime.get("history_limit", 100)),
        "drift_threshold": float(runtime.get("drift_threshold", 0.30)),
        "false_positive_threshold": float(runtime.get("false_positive_threshold", 0.20)),
        "model": str(top_level.get("model", "default.pkl")),
    }


def _telemetry_from_detection(detection: DetectionEvaluation, reference_at: str | None = None) -> dict[str, Any]:
    timestamp = reference_at or detection.telemetry_timestamp
    return {
        "provider_source": detection.evidence.provider_source,
        "timestamp": timestamp,
        "sample_window_seconds": 1.0,
        "flows": [
            {
                "source": "0.0.0.0",
                "destination_port": detection.feature_vector.destination_port_distribution[0][0]
                if detection.feature_vector.destination_port_distribution
                else 0,
                "packets": detection.feature_vector.packet_rate,
                "bytes": detection.feature_vector.byte_rate,
                "connections": detection.feature_vector.connection_rate,
                "duration": detection.feature_vector.flow_duration,
                "protocol": detection.attack_type if detection.attack_type != "normal" else "tcp",
            }
        ],
        "flow_state": {"flow_count": 1, "telemetry_present": True},
        "telemetry_state": {"collector_reachable": True, "active_flow_count": 1},
        "freshness_state": {"stale": False, "sample_interval_seconds": 1.0},
        "replay_mode": False,
    }


def _attack_frequency(policy_history_payload: dict[str, Any], attack_type: str) -> float:
    entries = policy_history_payload.get("entries", [])
    if not isinstance(entries, list):
        return 1.0
    return float(len([item for item in entries if isinstance(item, dict) and item.get("attack_type") == attack_type]) + 1)


def _timestamp(reference_at: str | None, detection: DetectionEvaluation, telemetry: dict[str, Any]) -> datetime:
    value = reference_at or str(telemetry.get("timestamp", detection.telemetry_timestamp))
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def train_ml_model(
    config: dict[str, Any],
    detection: DetectionEvaluation | None = None,
    telemetry: dict[str, Any] | None = None,
    reference_at: str | None = None,
) -> MLDetectionEvaluation:
    return evaluate_ml_detection(config, detection=detection, telemetry=telemetry, reference_at=reference_at, force_retrain=True)


def retrain_ml_model(
    config: dict[str, Any],
    detection: DetectionEvaluation | None = None,
    telemetry: dict[str, Any] | None = None,
    reference_at: str | None = None,
) -> MLDetectionEvaluation:
    return evaluate_ml_detection(config, detection=detection, telemetry=telemetry, reference_at=reference_at, force_retrain=True)


def evaluate_ml_detection(
    config: dict[str, Any],
    detection: DetectionEvaluation | None = None,
    telemetry: dict[str, Any] | None = None,
    reference_at: str | None = None,
    force_retrain: bool = False,
) -> MLDetectionEvaluation:
    settings = _settings(config)
    detection_evaluation = detection or evaluate_detection(config, telemetry=telemetry, reference_at=reference_at)
    payload = telemetry or _telemetry_from_detection(detection_evaluation, reference_at=reference_at)
    from nsddos.runtime.mitigation.engine import latest_mitigation_evidence
    from nsddos.runtime.policy.history import latest_history_payload

    policy_history = latest_history_payload()
    mitigation_payload = latest_mitigation_evidence()
    feedback_state = load_feedback() or build_feedback_state(policy_history, mitigation_payload)
    attack_frequency = _attack_frequency(policy_history, detection_evaluation.attack_type)
    features = extract_ml_features(payload, detection_evaluation, feedback_state, attack_frequency)
    dataset = build_dataset_snapshot(
        load_dataset(),
        build_dataset_row(
            detection_evaluation,
            features,
            str(mitigation_payload.get("mitigation_action", "alert_only")),
            str(mitigation_payload.get("mitigation_action", "alert_only")) != "alert_only",
            reference_at or detection_evaluation.telemetry_timestamp,
        ),
        limit=settings["dataset_limit"],
        reference_at=reference_at or detection_evaluation.telemetry_timestamp,
    )
    baseline = build_baseline(dataset)
    anomaly_value, anomaly_confidence = anomaly_score(features, baseline)
    current_model = load_model()
    needs_retrain = force_retrain or registry_retraining_required(
        current_model,
        dataset.row_count,
        settings["retrain_threshold"],
    )
    if current_model is None:
        current_model = train_model(dataset, settings["model_family"], version_seed=settings["model"])
    elif needs_retrain:
        current_model = retrain_model(dataset, current_model)
    metrics = load_metrics() or MLEvaluationMetrics(0.0, 0.0, feedback_state.false_positive_score, 0.0, 0.0)
    inference = run_inference(current_model, features, anomaly_score=anomaly_value)
    evaluation_metrics = compute_evaluation_metrics(dataset, feedback_state)
    drift_state = detect_drift(features, baseline, metrics, anomaly_value)
    false_positive_score = max(
        feedback_state.false_positive_score,
        (1.0 - inference.attack_probability) if detection_evaluation.attack_detected and inference.predicted_attack_type == "normal" else 0.0,
    )
    retraining_required = (
        force_retrain
        or drift_state.drift_score >= settings["drift_threshold"]
        or false_positive_score >= settings["false_positive_threshold"]
    )
    diagnostics = build_diagnostics(
        evaluation_metrics=evaluation_metrics,
        drift_state=drift_state,
        feedback_state=feedback_state,
        anomaly_score=anomaly_confidence,
    )
    evaluation = MLDetectionEvaluation(
        model_id=current_model.model_id,
        attack_probability=inference.attack_probability,
        predicted_attack_type=inference.predicted_attack_type,
        confidence_score=inference.confidence_score,
        anomaly_score=anomaly_value,
        drift_score=drift_state.drift_score,
        false_positive_score=false_positive_score,
        retraining_required=retraining_required,
        model_version=current_model.model_version,
        timestamp=_timestamp(reference_at, detection_evaluation, payload),
        feature_vector=features,
        dataset=dataset,
        training_state=current_model,
        inference=inference,
        baseline=baseline,
        drift=drift_state,
        evaluation_metrics=evaluation_metrics,
        feedback_state=feedback_state,
        diagnostics=diagnostics,
    )
    errors = validate_ml_evaluation(evaluation)
    if errors:
        raise ValueError(f"ml evaluation invalid: {','.join(errors)}")
    persist_dataset(dataset)
    persist_model(current_model)
    persist_metrics(evaluation_metrics)
    persist_feedback(feedback_state)
    persist_latest(evaluation)
    return evaluation
