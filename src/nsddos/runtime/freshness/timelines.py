"""Temporal lineage helpers."""

from __future__ import annotations

from datetime import datetime, timezone


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_time(value: str | None) -> str:
    return value or now_utc_iso()


def lineage(
    created_at: str, observed_at: str, synchronized_at: str
) -> tuple[str, str, str]:
    return (created_at, observed_at, synchronized_at)
