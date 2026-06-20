"""Deterministic scheduling helpers."""

from __future__ import annotations


def resolve_partition_count(active_nodes: int, configured_count: int | None = None) -> int:
    """Return stable partition count."""
    if configured_count and configured_count > 0:
        return configured_count
    return max(1, active_nodes * 2)
