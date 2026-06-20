"""Deterministic ML subsystem contracts."""

from __future__ import annotations

ML_MODEL_FAMILIES = ("random_forest_style", "svm_style")
ML_CLASSIFICATION_STATES = ("benign", "suspicious", "attack", "critical_attack")
ML_PREDICTED_ATTACK_TYPES = (
    "normal",
    "syn_flood",
    "udp_flood",
    "icmp_flood",
    "http_flood",
    "slowloris",
    "connection_exhaustion",
    "volumetric_anomaly",
    "suspicious",
)

__all__ = [
    "ML_CLASSIFICATION_STATES",
    "ML_MODEL_FAMILIES",
    "ML_PREDICTED_ATTACK_TYPES",
]
