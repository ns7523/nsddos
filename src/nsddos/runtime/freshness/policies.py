"""Freshness policy declarations."""

from __future__ import annotations

DEFAULT_POLICY = {
    "exclude_expired": True,
    "degrade_stale_to_warn": True,
    "propagate_parent_staleness": True,
}
