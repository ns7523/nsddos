"""ML validation."""

from __future__ import annotations

from nsddos.runtime.ml.contracts import (
    ML_CLASSIFICATION_STATES,
    ML_MODEL_FAMILIES,
    ML_PREDICTED_ATTACK_TYPES,
)
from nsddos.runtime.ml.models import (
    MLDetectionEvaluation,
    MLDatasetSnapshot,
    MLFeatureVector,
    MLTrainingState,
)


def validate_feature_vector(features: MLFeatureVector) -> list[str]:
    numeric = features.values()
    if any(value < 0 for value in numeric):
        return ["invalid_feature_vector"]
    return []


def validate_dataset(dataset: MLDatasetSnapshot) -> list[str]:
    errors: list[str] = []
    if dataset.row_count != len(dataset.rows):
        errors.append("malformed_dataset")
    for row in dataset.rows:
        if validate_feature_vector(row.feature_vector):
            errors.append("invalid_feature_vector")
    return sorted(set(errors))


def validate_model_state(model: MLTrainingState) -> list[str]:
    errors: list[str] = []
    if model.model_family not in ML_MODEL_FAMILIES:
        errors.append("invalid_model_state")
    if not 0.0 <= model.attack_threshold <= 1.0:
        errors.append("invalid_model_state")
    if not model.model_id or not model.model_version:
        errors.append("invalid_model_state")
    return sorted(set(errors))


def validate_ml_evaluation(evaluation: MLDetectionEvaluation) -> list[str]:
    errors = validate_feature_vector(evaluation.feature_vector)
    errors.extend(validate_dataset(evaluation.dataset))
    errors.extend(validate_model_state(evaluation.training_state))
    if evaluation.predicted_attack_type not in ML_PREDICTED_ATTACK_TYPES:
        errors.append("invalid_inference_output")
    if evaluation.inference.classification_state not in ML_CLASSIFICATION_STATES:
        errors.append("invalid_inference_output")
    for value in (
        evaluation.attack_probability,
        evaluation.confidence_score,
        evaluation.anomaly_score,
        evaluation.drift_score,
        evaluation.false_positive_score,
    ):
        if not 0.0 <= value <= 1.0:
            errors.append("confidence_corruption")
            break
    if evaluation.drift.distribution_change < 0:
        errors.append("drift_corruption")
    return sorted(set(errors))
