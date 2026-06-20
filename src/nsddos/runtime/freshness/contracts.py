"""Freshness contract requirements."""

from __future__ import annotations

REQUIRED_FRESHNESS_FIELDS = (
    "created_at",
    "observed_at",
    "synchronized_at",
    "freshness_window",
    "freshness_status",
    "validity_state",
    "replay_validity",
    "consistency_generation",
)
