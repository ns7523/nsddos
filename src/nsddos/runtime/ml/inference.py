"""Deterministic ML inference."""

from __future__ import annotations

import math

from nsddos.runtime.ml.classification import classify_probability
from nsddos.runtime.ml.models import MLFeatureVector, MLInferenceResult, MLTrainingState


def _distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if not left or not right:
        return 0.0
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right, strict=False)))


def run_inference(model: MLTrainingState, features: MLFeatureVector, anomaly_score: float = 0.0) -> MLInferenceResult:
    values = features.values()
    weighted_sum = sum(weight * min(value / 1000.0, 1.0) for weight, value in zip(model.feature_weights, values, strict=False))
    centroid_map = model.centroid_map()
    if not centroid_map:
        predicted_type = "normal"
        nearest_distance = 1.0
    else:
        ranked = sorted((key, _distance(values, centroid)) for key, centroid in centroid_map.items())
        predicted_type, nearest_distance = ranked[0]
    probability = max(0.0, min(1.0, (weighted_sum * 0.75) + (anomaly_score * 0.25)))
    if predicted_type == "normal" and probability >= model.attack_threshold:
        predicted_type = "suspicious"
    margin_score = max(0.0, 1.0 - min(nearest_distance / 2000.0, 1.0))
    confidence = max(0.0, min(1.0, (probability * 0.7) + (margin_score * 0.3)))
    classification_state = classify_probability(probability, anomaly_score, confidence)
    if classification_state == "benign":
        predicted_type = "normal"
    return MLInferenceResult(
        attack_probability=probability,
        predicted_attack_type=predicted_type,
        confidence_score=confidence,
        classification_state=classification_state,
        margin_score=margin_score,
    )
