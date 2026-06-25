"""ML registry helpers."""

from __future__ import annotations

from nsddos.runtime.ml.models import MLTrainingState
from nsddos.runtime.ml.persistence import load_model


def active_model() -> MLTrainingState | None:
    return load_model()


def active_model_version() -> str:
    model = load_model()
    return model.model_version if model is not None else ""


def retraining_required(
    model: MLTrainingState | None, dataset_size: int, threshold: float
) -> bool:
    if model is None:
        return True
    if dataset_size > model.trained_row_count:
        growth = (dataset_size - model.trained_row_count) / max(
            model.trained_row_count, 1
        )
        return growth >= threshold
    return False
