"""Freshness persistence contracts."""

from __future__ import annotations

PERSISTED_FIELDS = (
    "created_at",
    "observed_at",
    "synchronized_at",
    "freshness_window",
    "freshness_status",
    "validity_state",
    "replay_validity",
    "consistency_generation",
)
