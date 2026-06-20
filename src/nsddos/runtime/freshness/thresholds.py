"""Freshness thresholds."""

from __future__ import annotations

from nsddos.runtime.freshness.windows import WINDOWS


def threshold_summary() -> dict[str, dict[str, int]]:
    return {
        name: {
            "stale_after_seconds": window.stale_after_seconds,
            "max_age_seconds": window.max_age_seconds,
        }
        for name, window in WINDOWS.items()
    }
