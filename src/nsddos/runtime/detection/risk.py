"""Risk scoring."""

from __future__ import annotations

from nsddos.runtime.detection.models import RiskAssessment
from nsddos.runtime.detection.scoring import confidence_score


def assess_risk(signature: float, anomaly: float, intensity: float) -> RiskAssessment:
    """Build deterministic risk assessment."""
    risk_score = signature + anomaly + intensity
    confidence = confidence_score(signature, anomaly, intensity)
    if risk_score >= 8.0:
        level = "CRITICAL"
    elif risk_score >= 5.0:
        level = "HIGH"
    elif risk_score >= 2.5:
        level = "MEDIUM"
    else:
        level = "LOW"
    return RiskAssessment(
        risk_score=risk_score,
        risk_level=level,
        confidence_score=confidence,
        signature_score=signature,
        anomaly_score=anomaly,
        traffic_intensity_score=intensity,
    )
