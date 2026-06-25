"""Deterministic ML dataset builder."""

from __future__ import annotations

from datetime import datetime, timezone

from nsddos.runtime.detection.models import DetectionEvaluation
from nsddos.runtime.domain.identifiers import deterministic_id
from nsddos.runtime.ml.models import MLDatasetRow, MLDatasetSnapshot, MLFeatureVector


def build_dataset_row(
    detection: DetectionEvaluation,
    features: MLFeatureVector,
    policy_action: str,
    mitigation_success: bool,
    timestamp: str,
) -> MLDatasetRow:
    row_id = deterministic_id(
        "ml-dataset-row",
        f"{detection.attack_type}:{policy_action}:{timestamp}:{features.packet_rate:.4f}",
    )
    return MLDatasetRow(
        row_id=row_id,
        attack_label=detection.attack_detected,
        attack_type=detection.attack_type,
        policy_action=policy_action,
        mitigation_success=mitigation_success,
        confidence_score=detection.confidence_score,
        feature_vector=features,
        timestamp=timestamp,
    )


def build_dataset_snapshot(
    existing: MLDatasetSnapshot | None,
    row: MLDatasetRow,
    *,
    limit: int,
    reference_at: str | None = None,
) -> MLDatasetSnapshot:
    rows = list(existing.rows if existing is not None else ())
    if row.row_id not in {item.row_id for item in rows}:
        rows.append(row)
    rows = sorted(rows, key=lambda item: (item.timestamp, item.row_id))[-limit:]
    updated_at = reference_at or datetime.now(timezone.utc).isoformat()
    dataset_id = deterministic_id(
        "ml-dataset", f"{len(rows)}:{rows[-1].row_id if rows else 'empty'}"
    )
    return MLDatasetSnapshot(
        dataset_id=dataset_id,
        rows=tuple(rows),
        row_count=len(rows),
        updated_at=updated_at,
    )
