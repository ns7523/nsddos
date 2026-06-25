"""Deterministic freshness windows."""

from __future__ import annotations

from nsddos.runtime.freshness.models import FreshnessWindow

WINDOWS: dict[str, FreshnessWindow] = {
    "runtime": FreshnessWindow("runtime", max_age_seconds=900, stale_after_seconds=300),
    "topology": FreshnessWindow(
        "topology", max_age_seconds=600, stale_after_seconds=180
    ),
    "telemetry": FreshnessWindow(
        "telemetry", max_age_seconds=180, stale_after_seconds=60
    ),
    "replay": FreshnessWindow(
        "replay", max_age_seconds=86400, stale_after_seconds=3600
    ),
    "evidence": FreshnessWindow(
        "evidence", max_age_seconds=1800, stale_after_seconds=600
    ),
    "verification": FreshnessWindow(
        "verification", max_age_seconds=600, stale_after_seconds=180
    ),
    "synchronization": FreshnessWindow(
        "synchronization", max_age_seconds=300, stale_after_seconds=120
    ),
    "session": FreshnessWindow("session", max_age_seconds=300, stale_after_seconds=120),
    "graph": FreshnessWindow("graph", max_age_seconds=900, stale_after_seconds=300),
}


def get_window(scope: str) -> FreshnessWindow:
    return WINDOWS.get(scope, WINDOWS["runtime"])
