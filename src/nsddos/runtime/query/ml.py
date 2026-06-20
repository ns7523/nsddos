"""ML query adapters."""

from __future__ import annotations

from nsddos.runtime.ml import evaluate_ml_detection, latest_ml_evaluation, retrain_ml_model, train_ml_model


def query_ml_infer(config: dict, query) -> dict[str, object]:
    payload = latest_ml_evaluation()
    if not payload:
        payload = evaluate_ml_detection(config).to_dict()
    return {
        "items": [
            {
                "id": payload.get("model_id", "ml"),
                "type": "ml",
                "model_id": payload.get("model_id", ""),
                "attack_probability": payload.get("attack_probability", 0.0),
                "predicted_attack_type": payload.get("predicted_attack_type", "normal"),
                "confidence_score": payload.get("confidence_score", 0.0),
                "anomaly_score": payload.get("anomaly_score", 0.0),
                "drift_score": payload.get("drift_score", 0.0),
                "false_positive_score": payload.get("false_positive_score", 0.0),
                "retraining_required": payload.get("retraining_required", False),
                "model_version": payload.get("model_version", ""),
                "timestamp": payload.get("timestamp", ""),
            }
        ],
        "evaluation": payload,
    }


def query_ml_diagnostics(config: dict, query) -> dict[str, object]:
    payload = latest_ml_evaluation()
    if not payload:
        payload = evaluate_ml_detection(config).to_dict()
    diagnostics = payload.get("diagnostics", {})
    metrics = diagnostics.get("model_accuracy_metrics", {})
    drift = diagnostics.get("drift_metrics", {})
    return {
        "items": [
            {
                "id": "ml-diagnostics",
                "type": "ml_diagnostics",
                "precision": metrics.get("precision", 0.0),
                "recall": metrics.get("recall", 0.0),
                "false_positive_rate": metrics.get("false_positive_rate", 0.0),
                "confidence_quality": metrics.get("confidence_quality", 0.0),
                "drift_score": drift.get("drift_score", 0.0),
                "retraining_frequency": diagnostics.get("retraining_frequency", 0),
                "timestamp": payload.get("timestamp", ""),
            }
        ]
    }


def query_ml_train(config: dict, query) -> dict[str, object]:
    payload = train_ml_model(config).to_dict()
    return query_ml_infer(config, query) | {"training": payload}


def query_ml_retrain(config: dict, query) -> dict[str, object]:
    payload = retrain_ml_model(config).to_dict()
    return query_ml_infer(config, query) | {"retraining": payload}
