"""Freshness diagnostics."""

from __future__ import annotations

from typing import Any

from nsddos.runtime.freshness.metadata import FRESHNESS_METADATA
from nsddos.runtime.freshness.thresholds import threshold_summary


def explain_freshness() -> dict[str, Any]:
    return {
        "metadata": FRESHNESS_METADATA,
        "thresholds": threshold_summary(),
        "states": ["valid", "stale", "expired", "degraded", "replay_only", "inconsistent", "divergent"],
    }
