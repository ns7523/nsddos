"""Detection evidence generation."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from nsddos.runtime.detection.models import AttackClassification, DetectionEvidence, FeatureVector, RiskAssessment
from nsddos.runtime.domain.serialization import to_canonical_json


def build_detection_evidence(
    telemetry: dict[str, Any],
    features: FeatureVector,
    classification: AttackClassification,
    risk: RiskAssessment,
) -> DetectionEvidence:
    """Generate deterministic detection evidence hashes."""
    evidence_payload = {
        "telemetry": telemetry,
        "features": features.to_dict(),
    }
    classification_payload = {
        "classification": classification.to_dict(),
        "risk": risk.to_dict(),
    }
    return DetectionEvidence(
        evidence_hash=hashlib.sha256(to_canonical_json(evidence_payload).encode("utf-8")).hexdigest(),
        classification_generation=hashlib.sha256(to_canonical_json(classification_payload).encode("utf-8")).hexdigest(),
        provider_source=str(telemetry.get("provider_source", "unknown")),
        timestamp=str(telemetry.get("timestamp", datetime.now(timezone.utc).isoformat())),
    )
