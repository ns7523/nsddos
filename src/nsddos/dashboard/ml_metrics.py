"""Dashboard ML metrics."""

from __future__ import annotations

from nsddos.dashboard.contracts import DashboardSourceBundle, MLMetricsState


def build_ml_metrics_state(sources: DashboardSourceBundle) -> MLMetricsState:
    """Aggregate ML metrics."""
    ml = sources.ml
    diagnostics = ml.get("diagnostics", {})
    drift_metrics = diagnostics.get("drift_metrics", {})
    accuracy = diagnostics.get("model_accuracy_metrics", {})
    return MLMetricsState(
        ml_confidence=float(ml.get("confidence_score", 0.0)),
        drift_trend=(
            float(ml.get("drift_score", 0.0)),
            float(drift_metrics.get("drift_score", 0.0)),
        ),
        retraining_frequency=int(diagnostics.get("retraining_frequency", 0)),
        anomaly_trend=(float(ml.get("anomaly_score", 0.0)),),
        false_positive_trend=(
            float(accuracy.get("false_positive_rate", 0.0)),
            float(ml.get("false_positive_score", 0.0)),
        ),
    )
