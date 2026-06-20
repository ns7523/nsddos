"""Deterministic verification severity model."""

from __future__ import annotations

SEVERITIES = ("info", "warning", "degraded", "failed", "critical")

STATUS_TO_SEVERITY = {
    "pass": "info",
    "warn": "warning",
    "stale": "degraded",
    "fail": "failed",
}

SEVERITY_RANK = {
    "info": 0,
    "warning": 1,
    "degraded": 2,
    "failed": 3,
    "critical": 4,
}


def severity_for_status(status: str) -> str:
    """Map compatibility status to verification severity."""
    return STATUS_TO_SEVERITY.get(status, "warning")


def worst_severity(values: list[str]) -> str:
    """Return highest deterministic severity."""
    if not values:
        return "info"
    return max(values, key=lambda value: SEVERITY_RANK.get(value, 1))
