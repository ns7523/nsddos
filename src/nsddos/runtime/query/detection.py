"""Detection query adapter."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.detection import evaluate_detection
from nsddos.runtime.query.models import RuntimeQuery


def query_detection(config: dict[str, Any], query: RuntimeQuery) -> dict[str, Any]:
    evaluation = evaluate_detection(config)
    payload = evaluation.to_dict()
    return {
        "items": [
            {
                "id": "detection",
                "type": "detection",
                "attack_detected": payload["attack_detected"],
                "attack_type": payload["attack_type"],
                "confidence_score": payload["confidence_score"],
                "risk_level": payload["risk_level"],
                "evidence_hash": payload["evidence_hash"],
                "classification_generation": payload["classification_generation"],
                "detection_status": payload["detection_status"],
                "telemetry_timestamp": payload["telemetry_timestamp"],
                "baseline_source": payload["baseline_source"],
            }
        ],
        "evaluation": payload,
    }
