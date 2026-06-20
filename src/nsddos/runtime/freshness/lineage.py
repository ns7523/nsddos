"""Freshness lineage strategy."""

from __future__ import annotations


def propagate_state(parent_state: str, child_state: str) -> str:
    if parent_state in {"expired", "divergent", "inconsistent"}:
        return "degraded"
    if parent_state == "stale" and child_state == "valid":
        return "stale"
    return child_state
