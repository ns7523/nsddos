"""Deterministic ML training."""

from __future__ import annotations

from datetime import datetime, timezone

from nsddos.runtime.domain.identifiers import deterministic_id
from nsddos.runtime.ml.contracts import ML_MODEL_FAMILIES
from nsddos.runtime.ml.models import MLDatasetSnapshot, MLTrainingState

DEFAULT_WEIGHTS = (
    0.18,
    0.08,
    0.12,
    0.12,
    0.11,
    0.10,
    0.05,
    0.05,
    0.03,
    0.07,
    0.05,
    0.04,
)


def _mean(values: list[tuple[float, ...]]) -> tuple[float, ...]:
    if not values:
        return tuple(0.0 for _ in DEFAULT_WEIGHTS)
    width = len(values[0])
    return tuple(sum(item[index] for item in values) / len(values) for index in range(width))


def train_model(
    dataset: MLDatasetSnapshot,
    model_family: str,
    *,
    version_seed: str,
) -> MLTrainingState:
    if model_family not in ML_MODEL_FAMILIES:
        raise ValueError(f"unsupported model family: {model_family}")
    grouped: dict[str, list[tuple[float, ...]]] = {}
    attack_rows = 0
    for row in dataset.rows:
        grouped.setdefault(row.attack_type, []).append(row.feature_vector.values())
        if row.attack_label:
            attack_rows += 1
    centroids = tuple(sorted((key, _mean(value)) for key, value in grouped.items()))
    threshold = max(0.25, min(0.8, attack_rows / max(dataset.row_count, 1)))
    model_version = deterministic_id("ml-model-version", f"{model_family}:{version_seed}:{dataset.dataset_id}")
    model_id = deterministic_id("ml-model", f"{model_family}:{model_version}:{dataset.row_count}")
    return MLTrainingState(
        model_id=model_id,
        model_family=model_family,
        model_version=model_version,
        attack_threshold=threshold,
        type_centroids=centroids,
        feature_weights=DEFAULT_WEIGHTS,
        trained_row_count=dataset.row_count,
        trained_at=datetime.now(timezone.utc).isoformat(),
    )


def retrain_model(dataset: MLDatasetSnapshot, current: MLTrainingState) -> MLTrainingState:
    return train_model(dataset, current.model_family, version_seed=f"retrain:{dataset.dataset_id}:{current.model_family}")
