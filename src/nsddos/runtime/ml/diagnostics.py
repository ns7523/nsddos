"""ML diagnostics."""

from __future__ import annotations

from nsddos.runtime.ml.models import MLDetectionEvaluation, MLDiagnostics


def build_diagnostics(
    *,
    evaluation_metrics,
    drift_state,
    feedback_state,
    anomaly_score: float,
) -> MLDiagnostics:
    return MLDiagnostics(
        model_accuracy_metrics=evaluation_metrics,
        drift_metrics=drift_state,
        retraining_frequency=feedback_state.retraining_frequency,
        false_positive_diagnostics=feedback_state.false_positive_score,
        anomaly_score_trend=anomaly_score,
    )


def explain_ml(evaluation: MLDetectionEvaluation) -> dict[str, object]:
    payload = evaluation.to_dict()
    payload["mode"] = "deterministic_ml"
    payload["persistence"] = "latest_history_model_dataset_metrics_feedback"
    return payload
