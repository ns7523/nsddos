"""ML classification mapping."""

from __future__ import annotations


def classify_probability(attack_probability: float, anomaly_score: float, confidence_score: float) -> str:
    if attack_probability >= 0.85 or anomaly_score >= 0.85:
        return "critical_attack"
    if attack_probability >= 0.60:
        return "attack"
    if attack_probability >= 0.35 or confidence_score >= 0.45:
        return "suspicious"
    return "benign"
