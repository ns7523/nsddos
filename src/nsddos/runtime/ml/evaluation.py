"""Deterministic ML metrics evaluation."""

from __future__ import annotations

from nsddos.runtime.ml.models import MLDatasetSnapshot, MLEvaluationMetrics, MLFeedbackState


def compute_evaluation_metrics(dataset: MLDatasetSnapshot, feedback: MLFeedbackState) -> MLEvaluationMetrics:
    rows = dataset.rows
    if not rows:
        return MLEvaluationMetrics(0.0, 0.0, 0.0, 0.0, 0.0)
    positives = sum(1 for row in rows if row.attack_label)
    mitigated = sum(1 for row in rows if row.mitigation_success)
    successful_attacks = sum(1 for row in rows if row.attack_label and row.mitigation_success)
    precision = successful_attacks / max(mitigated, 1)
    recall = successful_attacks / max(positives, 1)
    false_positive_rate = feedback.false_positive_score
    false_negative_rate = max(0.0, min(1.0, 1.0 - recall))
    confidence_quality = max(0.0, min(1.0, (precision * 0.4) + (recall * 0.4) + ((1.0 - false_positive_rate) * 0.2)))
    return MLEvaluationMetrics(
        precision=precision,
        recall=recall,
        false_positive_rate=false_positive_rate,
        false_negative_rate=false_negative_rate,
        confidence_quality=confidence_quality,
    )
