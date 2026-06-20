"""Verification categories."""

from __future__ import annotations

CATEGORIES = (
    "environment",
    "orchestration",
    "collection",
    "normalization",
    "reconciliation",
    "convergence",
    "persistence",
    "reproducibility",
    "topology",
    "datapath",
    "telemetry",
    "temporal",
    "integrity",
)

CATEGORY_DEPENDENCIES = {
    "orchestration": ["environment"],
    "collection": ["environment"],
    "normalization": ["collection"],
    "reconciliation": ["normalization"],
    "convergence": ["reconciliation"],
    "telemetry": ["collection"],
    "topology": ["normalization"],
    "datapath": ["topology"],
    "temporal": ["convergence"],
    "integrity": ["persistence", "reconciliation", "convergence"],
}
